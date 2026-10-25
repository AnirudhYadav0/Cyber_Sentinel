from datetime import datetime
from typing import Optional, List, Union
from fastapi import APIRouter, Query, Path, HTTPException, status, UploadFile, File

from app.schemas.events import (
    SecurityEventCreate,
    SecurityEventResponse,
    PaginatedEventsResponse,
    IngestionResponse,
)
from app.services.event_service import event_service

router = APIRouter(prefix="/api/events", tags=["Events"])


@router.get("", response_model=PaginatedEventsResponse)
def list_events(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    limit: Optional[int] = Query(default=None, ge=1, le=100, description="Alias for page_size"),
    skip: Optional[int] = Query(default=None, ge=0, description="Items to skip"),
    search: Optional[str] = Query(default=None, max_length=100),
    event_type: Optional[str] = Query(default=None, max_length=64),
    severity: Optional[str] = Query(default=None, max_length=20),
    outcome: Optional[str] = Query(default=None, max_length=20),
    start_time: Optional[datetime] = Query(default=None),
    end_time: Optional[datetime] = Query(default=None),
    sort_by: str = Query(default="timestamp", pattern="^(timestamp|severity|event_type|source|outcome)$"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
):
    """Retrieve security events with filtering, search, pagination, and sorting."""
    # Support Phase 1 limit/skip parameters if passed
    effective_page = page
    effective_page_size = page_size
    if limit is not None:
        effective_page_size = limit
    if skip is not None and effective_page_size > 0:
        effective_page = (skip // effective_page_size) + 1

    return event_service.get_events(
        page=effective_page,
        page_size=effective_page_size,
        search=search,
        event_type=event_type,
        severity=severity,
        outcome=outcome,
        start_time=start_time,
        end_time=end_time,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/{event_id}", response_model=SecurityEventResponse)
def get_event_by_id(
    event_id: str = Path(..., min_length=1, max_length=64, description="Unique event ID")
):
    """Retrieve a single security event by its identifier."""
    event = event_service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security event with ID '{event_id}' not found.",
        )
    return event


@router.post("/ingest", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
def ingest_events(
    payload: Union[SecurityEventCreate, List[SecurityEventCreate]],
):
    """Ingest single or batched security events."""
    events_list = payload if isinstance(payload, list) else [payload]
    if len(events_list) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size exceeds maximum limit of 1000 events.",
        )
    return event_service.ingest_events(events_list)


@router.post("/upload", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
async def upload_events_file(
    file: UploadFile = File(..., description="JSON or JSON Lines log file (.json, .jsonl, .ndjson, .log)")
):
    """Upload and ingest security telemetry from JSON or JSON Lines file."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file cannot be empty.",
        )

    result = event_service.parse_and_ingest_file(
        filename=file.filename,
        content=content,
    )
    return result
