from datetime import datetime, timezone
import uuid
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

VALID_ALERT_STATUSES = {"Open", "Investigating", "Resolved", "Dismissed"}
VALID_SEVERITIES = {"Critical", "High", "Medium", "Low", "Info"}


class AlertCreate(BaseModel):
    id: Optional[str] = None
    rule_id: str = Field(..., max_length=32)
    title: str = Field(..., max_length=128)
    detail: Optional[str] = Field(default=None, max_length=500)
    severity: str = Field(default="Medium")
    status: str = Field(default="Open")
    matched_count: int = Field(default=1, ge=0)
    event_ids: List[str] = Field(default_factory=list)
    dedup_key: Optional[str] = Field(default=None, max_length=128)
    analyst_notes: Optional[str] = Field(default=None, max_length=1000)
    assigned_to: Optional[str] = Field(default=None, max_length=64)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        norm = v.capitalize()
        if norm not in VALID_ALERT_STATUSES:
            raise ValueError(f"Invalid alert status: '{v}'. Allowed: {', '.join(VALID_ALERT_STATUSES)}")
        return norm

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        norm = v.capitalize()
        if norm not in VALID_SEVERITIES:
            raise ValueError(f"Invalid alert severity: '{v}'. Allowed: {', '.join(VALID_SEVERITIES)}")
        return norm


class AlertUpdate(BaseModel):
    status: Optional[str] = None
    analyst_notes: Optional[str] = Field(default=None, max_length=1000)
    assigned_to: Optional[str] = Field(default=None, max_length=64)

    @field_validator("status")
    @classmethod
    def validate_status_transition(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        norm = v.capitalize()
        if norm not in VALID_ALERT_STATUSES:
            raise ValueError(f"Invalid alert status: '{v}'. Allowed: {', '.join(VALID_ALERT_STATUSES)}")
        return norm


class AlertResponse(BaseModel):
    id: str
    rule_id: str
    title: str
    detail: Optional[str] = None
    severity: str
    status: str
    matched_count: int
    event_ids: List[str] = []
    dedup_key: Optional[str] = None
    analyst_notes: Optional[str] = None
    assigned_to: Optional[str] = None
    timestamp: datetime
    updated_at: datetime


class PaginatedAlertsResponse(BaseModel):
    items: List[AlertResponse]
    total: int
    page: int
    page_size: int
