from datetime import datetime, timezone
import json
import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError, DuplicateKeyError

from app.database import db_manager
from app.schemas.events import (
    SecurityEventCreate,
    SecurityEventResponse,
    PaginatedEventsResponse,
    IngestionResponse,
)

logger = logging.getLogger("cybersentinel.events")

ALLOWED_SORT_FIELDS = {
    "timestamp": "timestamp",
    "severity": "severity",
    "event_type": "event_type",
    "source": "source",
    "outcome": "outcome",
}


class EventService:
    @staticmethod
    def get_events(
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        outcome: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sort_by: str = "timestamp",
        sort_dir: str = "desc",
    ) -> PaginatedEventsResponse:
        """Query security events with pagination, search, and filtering."""
        db = db_manager.get_database()
        if db is None:
            return PaginatedEventsResponse(items=[], events=[], total=0, page=page, page_size=page_size)

        # Build query filter safely
        query: Dict[str, Any] = {}

        if event_type:
            query["event_type"] = event_type.strip().lower()

        if severity:
            query["severity"] = severity.capitalize()

        if outcome:
            query["outcome"] = outcome.strip().lower()

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
                {"description": regex_cond},
                {"username": regex_cond},
                {"source_ip": regex_cond},
                {"source": regex_cond},
                {"event_type": regex_cond},
            ]

        try:
            total = db.security_events.count_documents(query)

            # Sorting
            sort_field = ALLOWED_SORT_FIELDS.get(sort_by, "timestamp")
            sort_order = DESCENDING if sort_dir.lower() == "desc" else ASCENDING

            skip = (page - 1) * page_size
            cursor = (
                db.security_events.find(query, {"_id": 0})
                .sort(sort_field, sort_order)
                .skip(skip)
                .limit(page_size)
            )

            items = [SecurityEventResponse(**doc) for doc in cursor]
            return PaginatedEventsResponse(
                items=items,
                events=items,
                total=total,
                page=page,
                page_size=page_size,
            )
        except PyMongoError as err:
            logger.error(f"MongoDB query error in get_events: {err.__class__.__name__}")
            return PaginatedEventsResponse(items=[], events=[], total=0, page=page, page_size=page_size)

    @staticmethod
    def get_event_by_id(event_id: str) -> Optional[SecurityEventResponse]:
        """Fetch single event by its unique ID."""
        db = db_manager.get_database()
        if db is None:
            return None
        try:
            doc = db.security_events.find_one({"id": event_id}, {"_id": 0})
            if doc:
                return SecurityEventResponse(**doc)
            return None
        except PyMongoError as err:
            logger.error(f"Error fetching event {event_id}: {err.__class__.__name__}")
            return None

    @staticmethod
    def ingest_events(events: List[SecurityEventCreate]) -> IngestionResponse:
        """Validate, deduplicate, and persist incoming security events."""
        db = db_manager.get_database()
        if db is None:
            return IngestionResponse(
                created=0,
                rejected=len(events),
                duplicates=0,
                errors=["Database is unavailable or not connected."],
            )

        created = 0
        duplicates = 0
        rejected = 0
        errors: List[str] = []

        for evt in events:
            try:
                data = evt.model_dump()
                # Ensure UTC timestamp
                if isinstance(data.get("timestamp"), str):
                    data["timestamp"] = datetime.fromisoformat(data["timestamp"])

                # Insert one
                db.security_events.insert_one(data)
                created += 1
            except DuplicateKeyError:
                duplicates += 1
            except Exception as ex:
                rejected += 1
                errors.append(f"Event {evt.id or 'unknown'}: {str(ex)[:100]}")

        return IngestionResponse(
            created=created,
            rejected=rejected,
            duplicates=duplicates,
            errors=errors[:10],  # Bound error responses
        )

    @staticmethod
    def parse_and_ingest_file(
        filename: str, content: bytes, max_file_size: int = 10 * 1024 * 1024, max_records: int = 5000
    ) -> IngestionResponse:
        """Safely parse uploaded JSON or JSON Lines and ingest normalized records."""
        if len(content) > max_file_size:
            return IngestionResponse(
                created=0,
                rejected=1,
                duplicates=0,
                errors=[f"File size exceeds maximum allowed limit of {max_file_size // (1024 * 1024)}MB."],
            )

        lower_name = filename.lower()
        if not (lower_name.endswith(".json") or lower_name.endswith(".jsonl") or lower_name.endswith(".ndjson") or lower_name.endswith(".log")):
            return IngestionResponse(
                created=0,
                rejected=1,
                duplicates=0,
                errors=["Unsupported file format. Please upload .json, .jsonl, .ndjson, or .log files."],
            )

        events_to_create: List[SecurityEventCreate] = []
        parse_errors: List[str] = []

        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            return IngestionResponse(
                created=0,
                rejected=1,
                duplicates=0,
                errors=["File encoding must be valid UTF-8."],
            )

        # Try parsing as JSON array/object first
        if lower_name.endswith(".json"):
            try:
                parsed = json.loads(text)
                items = parsed if isinstance(parsed, list) else [parsed]
                if len(items) > max_records:
                    return IngestionResponse(
                        created=0,
                        rejected=1,
                        duplicates=0,
                        errors=[f"Record count exceeds maximum batch limit of {max_records}."],
                    )
                for item in items:
                    try:
                        events_to_create.append(SecurityEventCreate(**item))
                    except Exception as err:
                        parse_errors.append(f"Validation error on record: {str(err)[:80]}")
            except json.JSONDecodeError:
                # Fallback to line by line JSON
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                if len(lines) > max_records:
                    return IngestionResponse(
                        created=0,
                        rejected=1,
                        duplicates=0,
                        errors=[f"Record count exceeds maximum batch limit of {max_records}."],
                    )
                for line in lines:
                    try:
                        data = json.loads(line)
                        events_to_create.append(SecurityEventCreate(**data))
                    except Exception as err:
                        parse_errors.append(f"Invalid JSON line: {str(err)[:80]}")
        else:
            # Line-by-line JSON (JSONL / NDJSON / LOG)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if len(lines) > max_records:
                return IngestionResponse(
                    created=0,
                    rejected=1,
                    duplicates=0,
                    errors=[f"Record count exceeds maximum batch limit of {max_records}."],
                )
            for line in lines:
                try:
                    data = json.loads(line)
                    events_to_create.append(SecurityEventCreate(**data))
                except Exception as err:
                    parse_errors.append(f"Invalid JSON line: {str(err)[:80]}")

        # Ingest parsed records
        res = EventService.ingest_events(events_to_create)
        res.rejected += len(parse_errors)
        res.errors.extend(parse_errors[:5])
        return res


event_service = EventService()
