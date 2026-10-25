from datetime import datetime, timezone, timedelta
import hashlib
from typing import List, Dict, Any, Optional
from app.detection.schemas import RuleConfig, DetectionResult
from app.schemas.events import SecurityEventResponse

DEFAULT_RULES = [
    RuleConfig(
        id="AUTH-001",
        name="Repeated Failed Logins",
        description="Identifies repeated failed authentication attempts against accounts or from a single IP source within a rolling time window.",
        enabled=True,
        severity="Critical",
        threshold=5,
        window_minutes=10,
        event_types=["auth.login_failed"],
        parameters={"group_by": "source_ip"},
    ),
    RuleConfig(
        id="AUTH-002",
        name="Repeated Unauthorized Access",
        description="Detects repeated access-denied (HTTP 401/403 or permission denied) security events across endpoints.",
        enabled=True,
        severity="High",
        threshold=5,
        window_minutes=10,
        event_types=["auth.access_denied"],
        parameters={"group_by": "source_ip"},
    ),
    RuleConfig(
        id="TRAFFIC-001",
        name="Unusual Request Volume",
        description="Flags request volume that exceeds the established baseline for an individual client or API endpoint.",
        enabled=True,
        severity="Medium",
        threshold=30,
        window_minutes=5,
        event_types=["api.request"],
        parameters={"group_by": "source_ip"},
    ),
    RuleConfig(
        id="PRIV-001",
        name="Unexpected Privileged Action",
        description="Monitors and flags administrative or role modification actions that fall outside the configured allowed action policy.",
        enabled=True,
        severity="High",
        threshold=1,
        window_minutes=30,
        event_types=["privilege.action"],
        parameters={
            "allowed_actions": ["read_config", "view_audit", "rotate_session", "read_telemetry"],
        },
    ),
]


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class BaseRuleEvaluator:
    """Base evaluator for security threat detection rules."""

    def __init__(self, config: RuleConfig):
        self.config = config

    def evaluate(self, events: List[SecurityEventResponse], window_start: datetime, window_end: datetime) -> List[DetectionResult]:
        raise NotImplementedError


class Auth001Evaluator(BaseRuleEvaluator):
    """
    AUTH-001: Repeated Failed Logins.
    Limitations:
    - May trigger on legitimate users who forgot passwords or mobile devices with cached stale tokens.
    - Distributed attacks with high IP diversity may remain below individual IP thresholds.
    """

    def evaluate(self, events: List[SecurityEventResponse], window_start: datetime, window_end: datetime) -> List[DetectionResult]:
        if not self.config.enabled:
            return []

        w_start = ensure_utc(window_start)
        w_end = ensure_utc(window_end)

        # Filter events in window
        matched_events = [
            e for e in events
            if (e.event_type == "auth.login_failed" or e.outcome == "failure")
            and w_start <= ensure_utc(e.timestamp) <= w_end
        ]

        # Group by IP / username
        groups: Dict[str, List[SecurityEventResponse]] = {}
        for evt in matched_events:
            key = evt.source_ip or evt.username or "unknown_source"
            groups.setdefault(key, []).append(evt)

        results: List[DetectionResult] = []
        for key, group_events in groups.items():
            count = len(group_events)
            if count >= self.config.threshold:
                event_ids = [e.id for e in group_events]
                # Stable deduplication key based on rule, target key, and time bucket
                time_bucket = w_end.strftime("%Y-%m-%d-%H")
                dedup_key = f"AUTH-001:{key}:{time_bucket}"

                results.append(
                    DetectionResult(
                        rule_id=self.config.id,
                        title=f"Repeated failed logins ({count} attempts)",
                        severity=self.config.severity,
                        detection_time=datetime.now(timezone.utc),
                        matched_event_ids=event_ids,
                        matched_event_count=count,
                        detection_reason=f"Observed {count} failed login attempts from '{key}' within {self.config.window_minutes} minutes, exceeding threshold of {self.config.threshold}.",
                        evidence_summary=f"{count} authentication failures recorded from source '{key}' between {w_start.strftime('%H:%M:%S')} and {w_end.strftime('%H:%M:%S')} UTC.",
                        source_identifier=key,
                        group_key=key,
                        dedup_key=dedup_key,
                        status="Open",
                    )
                )
        return results


class Auth002Evaluator(BaseRuleEvaluator):
    """
    AUTH-002: Repeated Unauthorized Access.
    Limitations:
    - Expired session tokens, broken client frontend loops, or web crawlers scanning paths can cause false positives.
    """

    def evaluate(self, events: List[SecurityEventResponse], window_start: datetime, window_end: datetime) -> List[DetectionResult]:
        if not self.config.enabled:
            return []

        w_start = ensure_utc(window_start)
        w_end = ensure_utc(window_end)

        matched_events = [
            e for e in events
            if (e.event_type == "auth.access_denied" or e.outcome == "denied")
            and w_start <= ensure_utc(e.timestamp) <= w_end
        ]

        groups: Dict[str, List[SecurityEventResponse]] = {}
        for evt in matched_events:
            key = evt.source_ip or evt.username or "unknown_source"
            groups.setdefault(key, []).append(evt)

        results: List[DetectionResult] = []
        for key, group_events in groups.items():
            count = len(group_events)
            if count >= self.config.threshold:
                event_ids = [e.id for e in group_events]
                time_bucket = w_end.strftime("%Y-%m-%d-%H")
                dedup_key = f"AUTH-002:{key}:{time_bucket}"

                results.append(
                    DetectionResult(
                        rule_id=self.config.id,
                        title=f"Repeated unauthorized access attempts ({count} requests)",
                        severity=self.config.severity,
                        detection_time=datetime.now(timezone.utc),
                        matched_event_ids=event_ids,
                        matched_event_count=count,
                        detection_reason=f"Observed {count} access-denied events from '{key}', exceeding threshold of {self.config.threshold}.",
                        evidence_summary=f"{count} unauthorized or denied requests from source '{key}'.",
                        source_identifier=key,
                        group_key=key,
                        dedup_key=dedup_key,
                        status="Open",
                    )
                )
        return results


class Traffic001Evaluator(BaseRuleEvaluator):
    """
    TRAFFIC-001: Unusual Request Volume.
    Limitations:
    - Legitimate data exports, batch operations, or frontend syncs may exceed thresholds.
    - Represents telemetry anomaly that warrants investigation rather than confirmed denial of service.
    """

    def evaluate(self, events: List[SecurityEventResponse], window_start: datetime, window_end: datetime) -> List[DetectionResult]:
        if not self.config.enabled:
            return []

        w_start = ensure_utc(window_start)
        w_end = ensure_utc(window_end)

        matched_events = [
            e for e in events
            if (e.event_type == "api.request")
            and w_start <= ensure_utc(e.timestamp) <= w_end
        ]

        groups: Dict[str, List[SecurityEventResponse]] = {}
        for evt in matched_events:
            key = evt.source_ip or evt.source or "unknown_source"
            groups.setdefault(key, []).append(evt)

        results: List[DetectionResult] = []
        for key, group_events in groups.items():
            count = len(group_events)
            if count >= self.config.threshold:
                event_ids = [e.id for e in group_events]
                time_bucket = w_end.strftime("%Y-%m-%d-%H")
                dedup_key = f"TRAFFIC-001:{key}:{time_bucket}"

                results.append(
                    DetectionResult(
                        rule_id=self.config.id,
                        title=f"Unusual request volume spike ({count} requests)",
                        severity=self.config.severity,
                        detection_time=datetime.now(timezone.utc),
                        matched_event_ids=event_ids,
                        matched_event_count=count,
                        detection_reason=f"Client '{key}' submitted {count} API requests within {self.config.window_minutes} minutes, exceeding volume threshold of {self.config.threshold}.",
                        evidence_summary=f"Surge of {count} requests from '{key}' within time window.",
                        source_identifier=key,
                        group_key=key,
                        dedup_key=dedup_key,
                        status="Open",
                    )
                )
        return results


class Priv001Evaluator(BaseRuleEvaluator):
    """
    PRIV-001: Unexpected Privileged Action.
    Limitations:
    - Emergency administrative interventions or break-glass maintenance will trigger alert.
    - Policy depends on accurate action categorization in event description or metadata.
    """

    def evaluate(self, events: List[SecurityEventResponse], window_start: datetime, window_end: datetime) -> List[DetectionResult]:
        if not self.config.enabled:
            return []

        w_start = ensure_utc(window_start)
        w_end = ensure_utc(window_end)

        allowed_actions = set(self.config.parameters.get("allowed_actions", []))

        # Check privilege.action events
        flagged_events: List[SecurityEventResponse] = []
        for e in events:
            if e.event_type != "privilege.action" or not (w_start <= ensure_utc(e.timestamp) <= w_end):
                continue

            action_name = None
            if e.metadata and isinstance(e.metadata, dict):
                action_name = e.metadata.get("action")
            if not action_name and e.description:
                action_name = e.description

            # If action not in allowed list, flag for review
            if action_name not in allowed_actions:
                flagged_events.append(e)

        groups: Dict[str, List[SecurityEventResponse]] = {}
        for evt in flagged_events:
            key = evt.username or evt.source_ip or "admin"
            groups.setdefault(key, []).append(evt)

        results: List[DetectionResult] = []
        for key, group_events in groups.items():
            count = len(group_events)
            if count >= self.config.threshold:
                event_ids = [e.id for e in group_events]
                time_bucket = window_end.strftime("%Y-%m-%d-%H")
                dedup_key = f"PRIV-001:{key}:{time_bucket}"

                sample_desc = group_events[0].description or "Unapproved privileged operation"
                results.append(
                    DetectionResult(
                        rule_id=self.config.id,
                        title=f"Unexpected privileged action by {key}",
                        severity=self.config.severity,
                        detection_time=datetime.now(timezone.utc),
                        matched_event_ids=event_ids,
                        matched_event_count=count,
                        detection_reason=f"User '{key}' performed {count} unapproved privileged action(s) ({sample_desc}) outside configured policy.",
                        evidence_summary=f"Privileged events outside allowed policy list: {', '.join(event_ids[:5])}.",
                        source_identifier=key,
                        group_key=key,
                        dedup_key=dedup_key,
                        status="Open",
                    )
                )
        return results


EVALUATOR_REGISTRY = {
    "AUTH-001": Auth001Evaluator,
    "AUTH-002": Auth002Evaluator,
    "TRAFFIC-001": Traffic001Evaluator,
    "PRIV-001": Priv001Evaluator,
}
