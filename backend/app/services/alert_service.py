from datetime import datetime, timezone
import logging
import re
import uuid
from typing import Optional, List, Dict, Any
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from app.database import db_manager
from app.schemas.alerts import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    PaginatedAlertsResponse,
)
from app.services.audit_service import audit_service

logger = logging.getLogger("cybersentinel.alerts")


class AlertService:
    @staticmethod
    def get_alerts(
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        rule_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> PaginatedAlertsResponse:
        """Fetch alerts with pagination, search, and filtering."""
        db = db_manager.get_database()
        if db is None:
            return PaginatedAlertsResponse(items=[], total=0, page=page, page_size=page_size)

        query: Dict[str, Any] = {}
        if severity:
            query["severity"] = severity.capitalize()
        if status:
            query["status"] = status.capitalize()
        if rule_id:
            query["rule_id"] = rule_id.strip()

        time_filter: Dict[str, Any] = {}
        if start_time:
            time_filter["$gte"] = start_time
        if end_time:
            time_filter["$lte"] = end_time
        if time_filter:
            query["timestamp"] = time_filter

        if search:
            safe_search = re.escape(search.strip())
            regex_cond = {"$regex": safe_search, "$options": "i"}
            query["$or"] = [
                {"id": regex_cond},
                {"title": regex_cond},
                {"detail": regex_cond},
                {"rule_id": regex_cond},
                {"analyst_notes": regex_cond},
            ]

        try:
            total = db.alerts.count_documents(query)
            skip = (page - 1) * page_size
            cursor = (
                db.alerts.find(query, {"_id": 0})
                .sort("timestamp", DESCENDING)
                .skip(skip)
                .limit(page_size)
            )
            items = [AlertResponse(**doc) for doc in cursor]
            return PaginatedAlertsResponse(items=items, total=total, page=page, page_size=page_size)
        except PyMongoError as err:
            logger.error(f"Error querying alerts: {err.__class__.__name__}")
            return PaginatedAlertsResponse(items=[], total=0, page=page, page_size=page_size)

    @staticmethod
    def get_alert_by_id(alert_id: str) -> Optional[AlertResponse]:
        """Fetch a single alert by ID."""
        db = db_manager.get_database()
        if db is None:
            return None
        try:
            doc = db.alerts.find_one({"id": alert_id}, {"_id": 0})
            if doc:
                return AlertResponse(**doc)
            return None
        except PyMongoError as err:
            logger.error(f"Error fetching alert {alert_id}: {err.__class__.__name__}")
            return None

    @staticmethod
    def create_alert(payload: AlertCreate) -> Optional[AlertResponse]:
        """Create a new alert record."""
        db = db_manager.get_database()
        if db is None:
            return None

        alert_id = payload.id or f"ALT-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)
        doc = payload.model_dump()
        doc["id"] = alert_id
        doc["timestamp"] = now
        doc["updated_at"] = now

        try:
            db.alerts.insert_one(doc)
            audit_service.log_action("create", "alert", alert_id, changes={"title": payload.title, "rule_id": payload.rule_id})
            return AlertResponse(**doc)
        except PyMongoError as err:
            logger.error(f"Error creating alert: {err.__class__.__name__}")
            return None

    @staticmethod
    def update_alert(alert_id: str, updates: AlertUpdate, user: Optional[str] = "analyst") -> Optional[AlertResponse]:
        """Update alert status, analyst notes, or assignment with audit logging."""
        db = db_manager.get_database()
        if db is None:
            return None

        current = db.alerts.find_one({"id": alert_id})
        if not current:
            return None

        update_dict: Dict[str, Any] = {}
        changes: Dict[str, Any] = {}

        if updates.status is not None:
            new_status = updates.status.capitalize()
            # Validate status transitions if necessary
            current_status = current.get("status", "Open")
            if current_status == "Resolved" and new_status == "Open":
                # Re-opening alert
                changes["status"] = {"from": current_status, "to": new_status}
            elif current_status != new_status:
                changes["status"] = {"from": current_status, "to": new_status}
            update_dict["status"] = new_status

        if updates.analyst_notes is not None:
            changes["analyst_notes"] = updates.analyst_notes
            update_dict["analyst_notes"] = updates.analyst_notes

        if updates.assigned_to is not None:
            changes["assigned_to"] = updates.assigned_to
            update_dict["assigned_to"] = updates.assigned_to

        if not update_dict:
            # No changes supplied, return current
            current.pop("_id", None)
            return AlertResponse(**current)

        now = datetime.now(timezone.utc)
        update_dict["updated_at"] = now

        try:
            db.alerts.update_one({"id": alert_id}, {"$set": update_dict})
            audit_service.log_action("update", "alert", alert_id, user=user, changes=changes)
            updated_doc = db.alerts.find_one({"id": alert_id}, {"_id": 0})
            if updated_doc:
                return AlertResponse(**updated_doc)
            return None
        except PyMongoError as err:
            logger.error(f"Error updating alert {alert_id}: {err.__class__.__name__}")
            return None


alert_service = AlertService()
