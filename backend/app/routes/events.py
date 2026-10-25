from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/events", tags=["Events"])


@router.get("")
def list_events(
    limit: int = Query(default=50, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
):
    """Retrieve security events. Empty in Phase 1 before database ingestion."""
    return {
        "events": [],
        "total": 0,
        "skip": skip,
        "limit": limit,
    }
