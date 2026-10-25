from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, Path, HTTPException, status

from app.schemas.alerts import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    PaginatedAlertsResponse,
)
from app.services.alert_service import alert_service

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("", response_model=PaginatedAlertsResponse)
def list_alerts(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(default=None, max_length=100),
    severity: Optional[str] = Query(default=None, max_length=20),
    status_filter: Optional[str] = Query(default=None, alias="status", max_length=20),
    rule_id: Optional[str] = Query(default=None, max_length=32),
    start_time: Optional[datetime] = Query(default=None),
    end_time: Optional[datetime] = Query(default=None),
):
    """Retrieve security alerts with pagination, search, and filtering."""
    return alert_service.get_alerts(
        page=page,
        page_size=page_size,
        search=search,
        severity=severity,
        status=status_filter,
        rule_id=rule_id,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert_by_id(
    alert_id: str = Path(..., min_length=1, max_length=64, description="Alert ID")
):
    """Retrieve details for a single threat alert."""
    alert = alert_service.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID '{alert_id}' was not found.",
        )
    return alert


@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(
    payload: AlertUpdate,
    alert_id: str = Path(..., min_length=1, max_length=64, description="Alert ID"),
):
    """Update alert triage status, analyst investigation notes, or assignment."""
    updated = alert_service.update_alert(alert_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID '{alert_id}' was not found or could not be updated.",
        )
    return updated
