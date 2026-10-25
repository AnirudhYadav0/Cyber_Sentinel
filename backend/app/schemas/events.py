from datetime import datetime, timezone
import uuid
import re
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, field_validator, model_validator

VALID_SEVERITIES = {"Critical", "High", "Medium", "Low", "Info"}
VALID_OUTCOMES = {"success", "failure", "denied", "unknown"}
ALLOWED_EVENT_TYPES = {
    "auth.login_success",
    "auth.login_failed",
    "auth.access_denied",
    "api.request",
    "privilege.action",
    "network.anomaly",
    "system.file_access",
    "data.exfiltration",
}

# Sensitive keys to filter out from metadata
SENSITIVE_KEYS = {"password", "secret", "token", "access_token", "api_key", "authorization", "auth_token"}


def sanitize_text(text: Optional[str]) -> Optional[str]:
    """Sanitize text fields against injection and control characters."""
    if text is None:
        return None
    # Strip dangerous characters / non-printable characters
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    return cleaned.strip()


def sanitize_metadata(meta: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Recursively scrub sensitive keys and tokens from metadata."""
    if not meta:
        return meta
    scrubbed = {}
    for k, v in meta.items():
        if str(k).lower() in SENSITIVE_KEYS:
            scrubbed[k] = "[REDACTED]"
        elif isinstance(v, dict):
            scrubbed[k] = sanitize_metadata(v)
        else:
            scrubbed[k] = v
    return scrubbed


class SecurityEventCreate(BaseModel):
    id: Optional[str] = Field(default=None, max_length=64)
    timestamp: Optional[datetime] = None
    event_type: str = Field(..., min_length=3, max_length=64)
    source_ip: Optional[str] = Field(default=None, max_length=45)
    username: Optional[str] = Field(default=None, max_length=64)
    outcome: Optional[str] = Field(default="unknown", max_length=20)
    source: Optional[str] = Field(default="system", max_length=64)
    severity: Optional[str] = Field(default="Info")
    description: Optional[str] = Field(default=None, max_length=500)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ALLOWED_EVENT_TYPES:
            # Allow custom dot-delimited formats e.g. service.action
            if not re.match(r"^[a-zA-Z0-9_\-]+(\.[a-zA-Z0-9_\-]+)+$", clean):
                raise ValueError(f"Invalid event_type format: '{v}'. Expected format like 'category.action'")
        return clean

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: Optional[str]) -> str:
        if not v:
            return "Info"
        norm = v.capitalize()
        if norm not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{v}'. Allowed: {', '.join(VALID_SEVERITIES)}")
        return norm

    @field_validator("outcome")
    @classmethod
    def validate_outcome(cls, v: Optional[str]) -> str:
        if not v:
            return "unknown"
        norm = v.strip().lower()
        if norm not in VALID_OUTCOMES:
            raise ValueError(f"Invalid outcome '{v}'. Allowed: {', '.join(VALID_OUTCOMES)}")
        return norm

    @field_validator("description", "source", "username", "source_ip")
    @classmethod
    def sanitize_strings(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_text(v)

    @model_validator(mode="after")
    def populate_defaults_and_sanitize(self):
        if not self.id:
            self.id = f"EVT-{uuid.uuid4().hex[:8].upper()}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc)
        elif self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)
        else:
            self.timestamp = self.timestamp.astimezone(timezone.utc)

        if self.metadata:
            self.metadata = sanitize_metadata(self.metadata)
        return self


class SecurityEventResponse(BaseModel):
    id: str
    timestamp: datetime
    event_type: str
    source_ip: Optional[str] = None
    username: Optional[str] = None
    outcome: Optional[str] = None
    source: Optional[str] = None
    severity: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaginatedEventsResponse(BaseModel):
    items: List[SecurityEventResponse]
    events: List[SecurityEventResponse]  # For backwards compatibility with Phase 1
    total: int
    page: int
    page_size: int


class IngestionResponse(BaseModel):
    created: int
    rejected: int
    duplicates: int
    errors: List[str] = []
