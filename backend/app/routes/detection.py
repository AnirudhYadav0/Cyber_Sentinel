from typing import List, Optional
from fastapi import APIRouter, Path, Query, HTTPException, status

from app.detection.schemas import (
    RuleConfig,
    RuleUpdate,
    DetectionRunRequest,
    DetectionRunSummary,
    PaginatedDetectionHistoryResponse,
)
from app.detection.engine import detection_engine

router = APIRouter(prefix="/api/detection", tags=["Threat Detection Engine"])


@router.post("/run", response_model=DetectionRunSummary)
def run_detection_scan(payload: Optional[DetectionRunRequest] = None):
    """
    Execute an on-demand detection scan over eligible events.
    Evaluates enabled rules, creates alerts, and deduplicates against existing findings.
    Note: In development/demo mode, this endpoint is accessible for simulated scans.
    """
    lookback = payload.lookback_minutes if payload else 60
    rule_ids = payload.rule_ids if payload else None
    return detection_engine.run_detection(lookback_minutes=lookback, rule_ids=rule_ids)


@router.get("/rules", response_model=List[RuleConfig])
def list_detection_rules():
    """Retrieve all configured detection rules and their current enabled states."""
    return detection_engine.get_rules()


@router.patch("/rules/{rule_id}", response_model=RuleConfig)
def update_detection_rule(
    payload: RuleUpdate,
    rule_id: str = Path(..., min_length=1, max_length=32, description="Rule ID e.g. AUTH-001"),
):
    """
    Tune detection rule configuration (e.g. threshold, time window, severity, enabled state).
    Rejects unauthorized or malformed inputs without allowing arbitrary code execution.
    """
    updated = detection_engine.update_rule_config(rule_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detection rule with ID '{rule_id}' was not found.",
        )
    return updated


@router.get("/history", response_model=PaginatedDetectionHistoryResponse)
def get_detection_history(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    """Retrieve audit history of past detection runs."""
    return detection_engine.get_history(page=page, page_size=page_size)
