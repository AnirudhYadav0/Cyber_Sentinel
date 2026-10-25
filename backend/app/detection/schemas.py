from datetime import datetime, timezone
import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator

VALID_SEVERITIES = {"Critical", "High", "Medium", "Low", "Info"}


class RuleConfig(BaseModel):
    id: str = Field(..., max_length=32, description="Unique rule ID e.g. AUTH-001")
    name: str = Field(..., max_length=128)
    description: str = Field(..., max_length=500)
    enabled: bool = True
    severity: str = "Medium"
    threshold: int = Field(default=5, ge=1)
    window_minutes: int = Field(default=10, ge=1, le=1440)
    event_types: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        norm = v.capitalize()
        if norm not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{v}'. Allowed: {', '.join(VALID_SEVERITIES)}")
        return norm


class RuleUpdate(BaseModel):
    enabled: Optional[bool] = None
    severity: Optional[str] = None
    threshold: Optional[int] = Field(default=None, ge=1, le=10000)
    window_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    parameters: Optional[Dict[str, Any]] = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        norm = v.capitalize()
        if norm not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{v}'. Allowed: {', '.join(VALID_SEVERITIES)}")
        return norm


class DetectionResult(BaseModel):
    rule_id: str
    title: str
    severity: str
    detection_time: datetime
    matched_event_ids: List[str]
    matched_event_count: int
    detection_reason: str
    evidence_summary: str
    source_identifier: Optional[str] = None
    group_key: str
    dedup_key: str
    status: str = "Open"


class DetectionRunRequest(BaseModel):
    lookback_minutes: Optional[int] = Field(default=60, ge=1, le=1440, description="Event lookback window in minutes")
    rule_ids: Optional[List[str]] = Field(default=None, description="Optional list of specific rule IDs to evaluate")


class DetectionRunSummary(BaseModel):
    run_id: str = Field(default_factory=lambda: f"RUN-{uuid.uuid4().hex[:8].upper()}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lookback_minutes: int
    events_examined: int
    rules_evaluated: int
    detections_generated: int
    alerts_created: int
    alerts_deduplicated: int
    detections: List[DetectionResult] = []


class PaginatedDetectionHistoryResponse(BaseModel):
    items: List[DetectionRunSummary]
    total: int
    page: int
    page_size: int
