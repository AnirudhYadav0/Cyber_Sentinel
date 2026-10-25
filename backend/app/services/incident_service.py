from datetime import datetime, timezone
import logging
import re
import uuid
from typing import Optional, List, Dict, Any
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from app.database import db_manager
from app.schemas.incidents import (
    IncidentCreate,
    IncidentUpdate,
    IncidentResponse,
    PaginatedIncidentsResponse,
)
from app.services.audit_service import audit_service

logger = logging.getLogger("cybersentinel.incidents")


class IncidentService:
    @staticmethod
    def get_incidents(
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> PaginatedIncidentsResponse:
        """Query incidents with pagination, search, and filters."""
        db = db_manager.get_database()
        if db is None:
            return PaginatedIncidentsResponse(items=[], total=0, page=page, page_size=page_size)

        query: Dict[str, Any] = {}
        if severity:
            query["severity"] = severity.capitalize()
        if status:
            query["status"] = status.capitalize()
        if assigned_to:
            query["assigned_to"] = assigned_to.strip()

        if search:
            safe_search = re.escape(search.strip())
            regex_cond = {"$regex": safe_search, "$options": "i"}
            query["$or"] = [
                {"id": regex_cond},
                {"title": regex_cond},
                {"description": regex_cond},
                {"assigned_to": regex_cond},
                {"investigation_notes": regex_cond},
            ]

        try:
            total = db.incidents.count_documents(query)
            skip = (page - 1) * page_size
            cursor = (
                db.incidents.find(query, {"_id": 0})
                .sort("created_at", DESCENDING)
                .skip(skip)
                .limit(page_size)
            )
            items = [IncidentResponse(**doc) for doc in cursor]
            return PaginatedIncidentsResponse(items=items, total=total, page=page, page_size=page_size)
        except PyMongoError as err:
            logger.error(f"Error querying incidents: {err.__class__.__name__}")
            return PaginatedIncidentsResponse(items=[], total=0, page=page, page_size=page_size)

    @staticmethod
    def get_incident_by_id(incident_id: str) -> Optional[IncidentResponse]:
        """Fetch single incident by ID."""
        db = db_manager.get_database()
        if db is None:
            return None
        try:
            doc = db.incidents.find_one({"id": incident_id}, {"_id": 0})
            if doc:
                return IncidentResponse(**doc)
            return None
        except PyMongoError as err:
            logger.error(f"Error fetching incident {incident_id}: {err.__class__.__name__}")
            return None

    @staticmethod
    def create_incident(payload: IncidentCreate, user: Optional[str] = "analyst") -> Optional[IncidentResponse]:
        """Create new incident with protected system timestamps."""
        db = db_manager.get_database()
        if db is None:
            return None

        incident_id = payload.id or f"INC-{uuid.uuid4().hex[:6].upper()}"
        now = datetime.now(timezone.utc)
        doc = payload.model_dump()
        doc["id"] = incident_id
        doc["created_at"] = now
        doc["updated_at"] = now

        try:
            db.incidents.insert_one(doc)
            audit_service.log_action("create", "incident", incident_id, user=user, changes={"title": payload.title, "severity": payload.severity})
            return IncidentResponse(**doc)
        except PyMongoError as err:
            logger.error(f"Error inserting incident: {err.__class__.__name__}")
            return None

    @staticmethod
    def update_incident(incident_id: str, updates: IncidentUpdate, user: Optional[str] = "analyst") -> Optional[IncidentResponse]:
        """Update incident without allowing client overwrite of protected system fields."""
        db = db_manager.get_database()
        if db is None:
            return None

        current = db.incidents.find_one({"id": incident_id})
        if not current:
            return None

        update_dict: Dict[str, Any] = {}
        changes: Dict[str, Any] = {}

        raw_updates = updates.model_dump(exclude_unset=True)
        # Protect system fields explicitly
        for protected in ("id", "created_at", "_id"):
            raw_updates.pop(protected, None)

        for k, v in raw_updates.items():
            if v is not None:
                update_dict[k] = v
                changes[k] = v

        if not update_dict:
            current.pop("_id", None)
            return IncidentResponse(**current)

        now = datetime.now(timezone.utc)
        update_dict["updated_at"] = now

        try:
            db.incidents.update_one({"id": incident_id}, {"$set": update_dict})
            audit_service.log_action("update", "incident", incident_id, user=user, changes=changes)
            updated_doc = db.incidents.find_one({"id": incident_id}, {"_id": 0})
            if updated_doc:
                return IncidentResponse(**updated_doc)
            return None
        except PyMongoError as err:
            logger.error(f"Error updating incident {incident_id}: {err.__class__.__name__}")
            return None


incident_service = IncidentService()
