from datetime import datetime, timezone, timedelta
import logging
from typing import Dict, List, Optional, Any
from pymongo.errors import PyMongoError

from app.database import db_manager
from app.detection.engine import detection_engine
from app.schemas.analytics import (
    DashboardSummary,
    TrendPoint,
    TrendsResponse,
    SeverityResponse,
    SourceDistributionPoint,
    SourceDistributionResponse,
)

logger = logging.getLogger("cybersentinel.analytics")


class AnalyticsService:
    @staticmethod
    def get_summary() -> DashboardSummary:
        """Calculate aggregated KPI metrics across events, alerts, and incidents."""
        db = db_manager.get_database()
        rules = detection_engine.get_rules()
        total_rules = len(rules)
        enabled_rules = sum(1 for r in rules if r.enabled)
        coverage = round((enabled_rules / total_rules * 100.0), 1) if total_rules > 0 else 0.0

        if db is None:
            return DashboardSummary(
                total_events=0,
                active_alerts=0,
                open_incidents=0,
                detection_coverage_pct=coverage,
                rules_triggered=0,
                total_rules=total_rules,
                enabled_rules=enabled_rules,
            )

        try:
            total_events = db.security_events.count_documents({})
            active_alerts = db.alerts.count_documents({"status": {"$in": ["Open", "Investigating"]}})
            open_incidents = db.incidents.count_documents({"status": {"$in": ["Open", "Investigating", "Contained"]}})
            rules_triggered = db.alerts.count_documents({})

            return DashboardSummary(
                total_events=total_events,
                active_alerts=active_alerts,
                open_incidents=open_incidents,
                detection_coverage_pct=coverage,
                rules_triggered=rules_triggered,
                total_rules=total_rules,
                enabled_rules=enabled_rules,
            )
        except PyMongoError as err:
            logger.error(f"Error querying dashboard summary: {err.__class__.__name__}")
            return DashboardSummary(
                total_events=0,
                active_alerts=0,
                open_incidents=0,
                detection_coverage_pct=coverage,
                rules_triggered=0,
                total_rules=total_rules,
                enabled_rules=enabled_rules,
            )

    @staticmethod
    def get_trends(range_str: str = "24h") -> TrendsResponse:
        """Aggregate security event volume over chronological time intervals."""
        db = db_manager.get_database()
        now = datetime.now(timezone.utc)

        # Standard 24h or 7d intervals
        is_7d = range_str.lower() in ("7d", "7_days", "week")
        hours_total = 168 if is_7d else 24
        bucket_count = 7
        interval_hours = hours_total / bucket_count
        start_time = now - timedelta(hours=hours_total)

        # Create bucket labels
        buckets: List[Dict[str, Any]] = []
        for i in range(bucket_count):
            b_start = start_time + timedelta(hours=i * interval_hours)
            b_end = start_time + timedelta(hours=(i + 1) * interval_hours)
            if is_7d:
                label = b_start.strftime("%a")
            else:
                label = "Now" if i == bucket_count - 1 else b_start.strftime("%-I %p")
            buckets.append({"start": b_start, "end": b_end, "label": label, "count": 0})

        if db is None:
            points = [TrendPoint(d=b["label"], v=0) for b in buckets]
            return TrendsResponse(time_range=range_str, points=points, peak_label="N/A", total_in_period=0)

        try:
            # Query events within range
            pipeline = [
                {"$match": {"timestamp": {"$gte": start_time, "$lte": now}}},
                {"$project": {"timestamp": 1}},
            ]
            events = list(db.security_events.aggregate(pipeline))

            # Distribute into buckets
            for evt in events:
                ts = evt.get("timestamp")
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts)
                    except Exception:
                        continue
                if not ts:
                    continue
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)

                for b in buckets:
                    if b["start"] <= ts < b["end"] or (b == buckets[-1] and b["start"] <= ts <= b["end"]):
                        b["count"] += 1
                        break

            points = [TrendPoint(d=b["label"], v=b["count"]) for b in buckets]
            total_in_period = sum(b["count"] for b in buckets)
            peak_bucket = max(buckets, key=lambda x: x["count"]) if buckets else None
            peak_label = f"Peak: {peak_bucket['label']}" if peak_bucket and peak_bucket["count"] > 0 else "Peak: None"

            return TrendsResponse(
                time_range=range_str,
                points=points,
                peak_label=peak_label,
                total_in_period=total_in_period,
            )
        except PyMongoError as err:
            logger.error(f"Error aggregating trends: {err.__class__.__name__}")
            points = [TrendPoint(d=b["label"], v=0) for b in buckets]
            return TrendsResponse(time_range=range_str, points=points, peak_label="N/A", total_in_period=0)

    @staticmethod
    def get_severity() -> SeverityResponse:
        """Aggregate severity distributions for alerts and security events."""
        db = db_manager.get_database()
        default_alerts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        default_events = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}

        if db is None:
            return SeverityResponse(
                alerts_by_severity=default_alerts,
                events_by_severity=default_events,
                total_alerts=0,
                total_events=0,
            )

        try:
            # Alerts severity aggregation
            alert_pipe = [{"$group": {"_id": "$severity", "count": {"$sum": 1}}}]
            for doc in db.alerts.aggregate(alert_pipe):
                sev = str(doc.get("_id", "")).capitalize()
                if sev in default_alerts:
                    default_alerts[sev] = doc.get("count", 0)

            # Events severity aggregation
            event_pipe = [{"$group": {"_id": "$severity", "count": {"$sum": 1}}}]
            for doc in db.security_events.aggregate(event_pipe):
                sev = str(doc.get("_id", "")).capitalize()
                if sev in default_events:
                    default_events[sev] = doc.get("count", 0)

            total_alerts = sum(default_alerts.values())
            total_events = sum(default_events.values())

            return SeverityResponse(
                alerts_by_severity=default_alerts,
                events_by_severity=default_events,
                total_alerts=total_alerts,
                total_events=total_events,
            )
        except PyMongoError as err:
            logger.error(f"Error querying severity distribution: {err.__class__.__name__}")
            return SeverityResponse(
                alerts_by_severity=default_alerts,
                events_by_severity=default_events,
                total_alerts=0,
                total_events=0,
            )

    @staticmethod
    def get_sources(range_str: str = "7d") -> SourceDistributionResponse:
        """Aggregate top event sources."""
        db = db_manager.get_database()
        if db is None:
            return SourceDistributionResponse(items=[], total=0)

        try:
            pipe = [
                {"$group": {"_id": "$source", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 7},
            ]
            docs = list(db.security_events.aggregate(pipe))
            items = [SourceDistributionPoint(d=doc["_id"] or "Unknown", v=doc["count"]) for doc in docs]
            total = sum(i.v for i in items)
            return SourceDistributionResponse(items=items, total=total)
        except PyMongoError as err:
            logger.error(f"Error querying sources: {err.__class__.__name__}")
            return SourceDistributionResponse(items=[], total=0)


analytics_service = AnalyticsService()
