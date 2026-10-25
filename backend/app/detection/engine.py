from datetime import datetime, timezone, timedelta
import logging
from typing import List, Optional, Dict, Any
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from app.database import db_manager
from app.detection.schemas import (
    RuleConfig,
    RuleUpdate,
    DetectionResult,
    DetectionRunSummary,
    PaginatedDetectionHistoryResponse,
)
from app.detection.rules import DEFAULT_RULES, EVALUATOR_REGISTRY
from app.schemas.events import SecurityEventResponse
from app.schemas.alerts import AlertCreate
from app.services.alert_service import alert_service

logger = logging.getLogger("cybersentinel.detection")


class DetectionEngine:
    """Core rule-based security threat detection engine."""

    def __init__(self):
        # In-memory dictionary of rules keyed by rule_id
        self._rules: Dict[str, RuleConfig] = {r.id: r.model_copy() for r in DEFAULT_RULES}

    def get_rules(self) -> List[RuleConfig]:
        """Fetch all configured detection rules."""
        db = db_manager.get_database()
        if db is not None:
            try:
                # If rules are saved in db, sync from db
                cursor = db.detection_rules.find({}, {"_id": 0})
                db_rules = list(cursor)
                if db_rules:
                    return [RuleConfig(**r) for r in db_rules]
                else:
                    # Seed default rules to DB
                    for r in self._rules.values():
                        db.detection_rules.update_one({"id": r.id}, {"$set": r.model_dump()}, upsert=True)
            except Exception as err:
                logger.warning(f"Could not read detection rules from DB: {err.__class__.__name__}")

        return list(self._rules.values())

    def get_rule_by_id(self, rule_id: str) -> Optional[RuleConfig]:
        """Fetch single rule by rule_id."""
        rules = self.get_rules()
        for r in rules:
            if r.id == rule_id:
                return r
        return None

    def update_rule_config(self, rule_id: str, updates: RuleUpdate) -> Optional[RuleConfig]:
        """Update configurable fields for a detection rule."""
        current = self.get_rule_by_id(rule_id)
        if not current:
            return None

        update_dict = updates.model_dump(exclude_unset=True)
        current_data = current.model_dump()
        current_data.update(update_dict)
        updated_rule = RuleConfig(**current_data)

        # Update in-memory
        self._rules[rule_id] = updated_rule

        # Update in DB if connected
        db = db_manager.get_database()
        if db is not None:
            try:
                db.detection_rules.update_one(
                    {"id": rule_id},
                    {"$set": updated_rule.model_dump()},
                    upsert=True,
                )
            except Exception as err:
                logger.error(f"Error persisting rule update for {rule_id}: {err.__class__.__name__}")

        return updated_rule

    def run_detection(self, lookback_minutes: int = 60, rule_ids: Optional[List[str]] = None) -> DetectionRunSummary:
        """Execute on-demand threat detection scan over bounded lookback window."""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=lookback_minutes)

        # Fetch eligible events from MongoDB
        db = db_manager.get_database()
        events: List[SecurityEventResponse] = []

        if db is not None:
            try:
                # Bounded query using timestamp index
                cursor = db.security_events.find(
                    {"timestamp": {"$gte": window_start, "$lte": now}},
                    {"_id": 0},
                ).sort("timestamp", DESCENDING).limit(5000)

                for doc in cursor:
                    try:
                        events.append(SecurityEventResponse(**doc))
                    except Exception:
                        continue  # Skip malformed event safely
            except PyMongoError as err:
                logger.error(f"MongoDB query failure during detection: {err.__class__.__name__}")

        all_rules = self.get_rules()
        active_rules = [
            r for r in all_rules
            if r.enabled and (rule_ids is None or r.id in rule_ids)
        ]

        detections: List[DetectionResult] = []
        rules_evaluated_count = 0

        # Evaluate rules
        for rule in active_rules:
            evaluator_cls = EVALUATOR_REGISTRY.get(rule.id)
            if not evaluator_cls:
                continue

            rules_evaluated_count += 1
            evaluator = evaluator_cls(rule)
            # Evaluate rule against events in rule's window
            rule_window_start = now - timedelta(minutes=rule.window_minutes)
            rule_detections = evaluator.evaluate(events, rule_window_start, now)
            detections.extend(rule_detections)

        alerts_created = 0
        alerts_deduplicated = 0

        # Alert persistence & deduplication
        if db is not None:
            for det in detections:
                try:
                    # Check if an alert with this dedup_key already exists
                    existing = db.alerts.find_one({"dedup_key": det.dedup_key})
                    if existing:
                        # Existing alert found. Deduplicate without modifying its triage status
                        alerts_deduplicated += 1
                    else:
                        # Create new alert
                        alert_payload = AlertCreate(
                            rule_id=det.rule_id,
                            title=det.title,
                            detail=det.detection_reason,
                            severity=det.severity,
                            status="Open",
                            matched_count=det.matched_event_count,
                            event_ids=det.matched_event_ids,
                            dedup_key=det.dedup_key,
                        )
                        alert_service.create_alert(alert_payload)
                        alerts_created += 1
                except Exception as err:
                    logger.warning(f"Error persisting detection alert: {err.__class__.__name__}")
        else:
            # When DB is disconnected, detections are generated in-memory without alert persistence
            alerts_created = len(detections)

        summary = DetectionRunSummary(
            lookback_minutes=lookback_minutes,
            events_examined=len(events),
            rules_evaluated=rules_evaluated_count,
            detections_generated=len(detections),
            alerts_created=alerts_created,
            alerts_deduplicated=alerts_deduplicated,
            detections=detections,
        )

        # Store in detection_history
        if db is not None:
            try:
                db.detection_history.insert_one(summary.model_dump())
            except Exception as err:
                logger.warning(f"Error saving detection history: {err.__class__.__name__}")

        return summary

    def get_history(self, page: int = 1, page_size: int = 20) -> PaginatedDetectionHistoryResponse:
        """Fetch past detection run summaries."""
        db = db_manager.get_database()
        if db is None:
            return PaginatedDetectionHistoryResponse(items=[], total=0, page=page, page_size=page_size)

        try:
            total = db.detection_history.count_documents({})
            skip = (page - 1) * page_size
            cursor = (
                db.detection_history.find({}, {"_id": 0})
                .sort("timestamp", DESCENDING)
                .skip(skip)
                .limit(page_size)
            )
            items = [DetectionRunSummary(**doc) for doc in cursor]
            return PaginatedDetectionHistoryResponse(items=items, total=total, page=page, page_size=page_size)
        except Exception as err:
            logger.error(f"Error fetching detection history: {err.__class__.__name__}")
            return PaginatedDetectionHistoryResponse(items=[], total=0, page=page, page_size=page_size)


detection_engine = DetectionEngine()
