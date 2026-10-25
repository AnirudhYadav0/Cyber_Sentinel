"""Event schemas placeholder for subsequent phases."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class SecurityEventBase(BaseModel):
    id: Optional[str] = None
    event_type: str = Field(..., description="e.g. auth.login_success, auth.login_failed")
    source_ip: Optional[str] = None
    username: Optional[str] = None
    outcome: Optional[str] = None
    source: Optional[str] = None
    severity: Optional[str] = "Info"
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
