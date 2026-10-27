from datetime import datetime
from typing import Optional, List, Union
from fastapi import APIRouter, Query, Path, HTTPException, status, UploadFile, File, Depends

from app.config import settings
from app.schemas.events import (
    SecurityEventCreate,
    SecurityEventResponse,
    PaginatedEventsResponse,
    IngestionResponse,
)
from app.services.event_service import event_service
from app.security.authentication import require_analyst, UserResponse
from app.security.rate_limiter import rate_limit_dependency
from app.services.audit_service import audit_service

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


@router.post(
    "/ingest",
    response_model=IngestionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_analyst),
        Depends(rate_limit_dependency("event_ingest", max_requests=120, window_seconds=60)),
    ],
)
def ingest_events(
    payload: Union[SecurityEventCreate, List[SecurityEventCreate]],
    current_user: UserResponse = Depends(require_analyst),
):
    """
    Ingest single or batched security events.
    Enforces authorization (analyst or admin), rate limits, and maximum batch size of 1000.
    """
    events_list = payload if isinstance(payload, list) else [payload]
    if len(events_list) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size exceeds maximum limit of 1000 events.",
        )
    return event_service.ingest_events(events_list)


@router.post(
    "/upload",
    response_model=IngestionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_analyst),
        Depends(rate_limit_dependency("event_upload", max_requests=30, window_seconds=60)),
    ],
)
async def upload_events_file(
    file: UploadFile = File(..., description="JSON or JSON Lines log file (.json, .jsonl, .ndjson, .log)"),
    current_user: UserResponse = Depends(require_analyst),
):
    """
    Upload and ingest security telemetry from JSON or JSON Lines file.
    Enforces strict chunked size limits (10MB) to prevent memory exhaustion DoS attacks.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    # Chunked read to protect server memory against massive payloads
    chunks = []
    total_read = 0
    max_size = settings.max_upload_size_bytes

    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total_read += len(chunk)
        if total_read > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File size exceeds maximum allowed limit of {max_size // (1024 * 1024)}MB.",
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file cannot be empty.",
        )

    result = event_service.parse_and_ingest_file(
        filename=file.filename,
        content=content,
        max_file_size=max_size,
    )

    audit_service.log_action(
        action="upload_events",
        resource_type="file",
        resource_id=file.filename,
        user=current_user.username,
        changes={
            "bytes_received": total_read,
            "created": result.created,
            "rejected": result.rejected,
            "duplicates": result.duplicates,
        },
    )
    return result
