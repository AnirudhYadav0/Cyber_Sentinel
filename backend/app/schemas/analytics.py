from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    total_events: int = 0
    active_alerts: int = 0
    open_incidents: int = 0
    detection_coverage_pct: float = 0.0
    rules_triggered: int = 0
    total_rules: int = 0
    enabled_rules: int = 0


class TrendPoint(BaseModel):
    d: str
    v: int


class TrendsResponse(BaseModel):
    time_range: str
    points: List[TrendPoint] = []
    peak_label: Optional[str] = None
    total_in_period: int = 0


class SeverityResponse(BaseModel):
    alerts_by_severity: Dict[str, int] = Field(default_factory=dict)
    events_by_severity: Dict[str, int] = Field(default_factory=dict)
    total_alerts: int = 0
    total_events: int = 0


class SourceDistributionPoint(BaseModel):
    d: str
    v: int


class SourceDistributionResponse(BaseModel):
    items: List[SourceDistributionPoint] = []
    total: int = 0
