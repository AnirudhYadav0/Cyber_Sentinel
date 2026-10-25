from datetime import datetime, timezone
import uuid
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

VALID_INCIDENT_STATUSES = {"Open", "Investigating", "Contained", "Resolved", "Closed"}
VALID_SEVERITIES = {"Critical", "High", "Medium", "Low"}


class IncidentCreate(BaseModel):
    id: Optional[str] = Field(default=None, max_length=32)
    title: str = Field(..., min_length=3, max_length=128)
    description: Optional[str] = Field(default=None, max_length=1000)
    severity: str = Field(default="Medium")
    status: str = Field(default="Open")
    assigned_to: Optional[str] = Field(default=None, max_length=64)
    alert_ids: List[str] = Field(default_factory=list)
    event_ids: List[str] = Field(default_factory=list)
    investigation_notes: Optional[str] = Field(default=None, max_length=2000)
    resolution_summary: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        norm = v.capitalize()
        if norm not in VALID_INCIDENT_STATUSES:
            raise ValueError(f"Invalid incident status: '{v}'. Allowed: {', '.join(VALID_INCIDENT_STATUSES)}")
        return norm

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        norm = v.capitalize()
        if norm not in VALID_SEVERITIES:
            raise ValueError(f"Invalid incident severity: '{v}'. Allowed: {', '.join(VALID_SEVERITIES)}")
        return norm


class IncidentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=128)
    description: Optional[str] = Field(default=None, max_length=1000)
    severity: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = Field(default=None, max_length=64)
    alert_ids: Optional[List[str]] = None
    event_ids: Optional[List[str]] = None
    investigation_notes: Optional[str] = Field(default=None, max_length=2000)
    resolution_summary: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        norm = v.capitalize()
        if norm not in VALID_INCIDENT_STATUSES:
            raise ValueError(f"Invalid incident status: '{v}'. Allowed: {', '.join(VALID_INCIDENT_STATUSES)}")
        return norm

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        norm = v.capitalize()
        if norm not in VALID_SEVERITIES:
            raise ValueError(f"Invalid incident severity: '{v}'. Allowed: {', '.join(VALID_SEVERITIES)}")
        return norm


class IncidentResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    severity: str
    status: str
    assigned_to: Optional[str] = None
    alert_ids: List[str] = []
    event_ids: List[str] = []
    investigation_notes: Optional[str] = None
    resolution_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaginatedIncidentsResponse(BaseModel):
    items: List[IncidentResponse]
    total: int
    page: int
    page_size: int
