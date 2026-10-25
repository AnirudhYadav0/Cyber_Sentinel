"""Incident schemas placeholder for subsequent phases."""
from typing import Optional, List
from pydantic import BaseModel


class IncidentBase(BaseModel):
    title: str
    severity: str
    status: str = "Open"
    assigned_to: Optional[str] = None
    alert_ids: List[str] = []
