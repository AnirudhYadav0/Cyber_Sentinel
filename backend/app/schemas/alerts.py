"""Alert schemas placeholder for subsequent phases."""
from typing import Optional, List
from pydantic import BaseModel


class AlertBase(BaseModel):
    rule_id: str
    title: str
    severity: str
    status: str = "Open"
    matched_count: int = 0
    event_ids: List[str] = []
