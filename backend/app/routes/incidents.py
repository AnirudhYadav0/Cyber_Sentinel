from typing import Optional
from fastapi import APIRouter, Query, Path, HTTPException, status, Depends

from app.schemas.incidents import (
    IncidentCreate,
    IncidentUpdate,
    IncidentResponse,
    PaginatedIncidentsResponse,
)
from app.services.incident_service import incident_service
from app.security.authentication import require_analyst, UserResponse

router = APIRouter(prefix="/api/incidents", tags=["Incidents"])


@router.get("", response_model=PaginatedIncidentsResponse)
def list_incidents(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(default=None, max_length=100),
    severity: Optional[str] = Query(default=None, max_length=20),
    status_filter: Optional[str] = Query(default=None, alias="status", max_length=20),
    assigned_to: Optional[str] = Query(default=None, max_length=64),
):
    """List incident response cases with pagination and filters."""
    return incident_service.get_incidents(
        page=page,
        page_size=page_size,
        search=search,
        severity=severity,
        status=status_filter,
        assigned_to=assigned_to,
    )


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
def create_incident(
    payload: IncidentCreate,
    current_user: UserResponse = Depends(require_analyst),
):
    """Create a new security incident case. Requires analyst or admin role."""
    created = incident_service.create_incident(payload, user=current_user.username)
    if not created:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create incident due to database error.",
        )
    return created


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident_by_id(
    incident_id: str = Path(..., min_length=1, max_length=64, description="Incident ID")
):
    """Retrieve details of a security incident case."""
    incident = incident_service.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' was not found.",
        )
    return incident


@router.patch(
    "/{incident_id}",
    response_model=IncidentResponse,
    dependencies=[Depends(require_analyst)],
)
def update_incident(
    payload: IncidentUpdate,
    incident_id: str = Path(..., min_length=1, max_length=64, description="Incident ID"),
    current_user: UserResponse = Depends(require_analyst),
):
    """Update investigation notes, severity, status, or assignment for an incident."""
    updated = incident_service.update_incident(incident_id, payload, user=current_user.username)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' was not found or could not be updated.",
        )
    return updated
