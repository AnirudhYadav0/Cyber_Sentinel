from typing import List, Optional
from fastapi import APIRouter, Path, Query, HTTPException, status, Depends

from app.detection.schemas import (
    RuleConfig,
    RuleUpdate,
    DetectionRunRequest,
    DetectionRunSummary,
    PaginatedDetectionHistoryResponse,
)
from app.detection.engine import detection_engine
from app.security.authentication import require_admin, require_analyst, UserResponse
from app.security.rate_limiter import rate_limit_dependency
from app.services.audit_service import audit_service

router = APIRouter(prefix="/api/detection", tags=["Threat Detection Engine"])


@router.post(
    "/run",
    response_model=DetectionRunSummary,
    dependencies=[
        Depends(require_analyst),
        Depends(rate_limit_dependency("detection_run", max_requests=30, window_seconds=60)),
    ],
)
def run_detection_scan(
    payload: Optional[DetectionRunRequest] = None,
    current_user: UserResponse = Depends(require_analyst),
):
    """
    Execute an on-demand detection scan over eligible events.
    Evaluates enabled rules, creates alerts, and deduplicates against existing findings.
    Requires analyst or admin role.
    """
    lookback = payload.lookback_minutes if payload else 60
    rule_ids = payload.rule_ids if payload else None
    summary = detection_engine.run_detection(lookback_minutes=lookback, rule_ids=rule_ids)

    audit_service.log_action(
        action="detection_scan",
        resource_type="detection",
        resource_id="scan",
        user=current_user.username,
        changes={
            "lookback_minutes": lookback,
            "rules_evaluated": summary.rules_evaluated,
            "alerts_created": summary.alerts_created,
        },
    )
    return summary


@router.get("/rules", response_model=List[RuleConfig])
def list_detection_rules():
    """Retrieve all configured detection rules and their current enabled states."""
    return detection_engine.get_rules()


@router.patch(
    "/rules/{rule_id}",
    response_model=RuleConfig,
    dependencies=[Depends(require_admin)],
)
def update_detection_rule(
    payload: RuleUpdate,
    rule_id: str = Path(..., min_length=1, max_length=32, description="Rule ID e.g. AUTH-001"),
    admin_user: UserResponse = Depends(require_admin),
):
    """
    Tune detection rule configuration (e.g. threshold, time window, severity, enabled state).
    Restricted to administrator role only.
    Rejects unauthorized or malformed inputs without allowing arbitrary code execution.
    """
    updated = detection_engine.update_rule_config(rule_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detection rule with ID '{rule_id}' was not found.",
        )

    audit_service.log_action(
        action="update_rule",
        resource_type="detection_rule",
        resource_id=rule_id,
        user=admin_user.username,
        changes=payload.model_dump(exclude_unset=True),
    )
    return updated


@router.get("/history", response_model=PaginatedDetectionHistoryResponse)
def get_detection_history(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    """Retrieve audit history of past detection runs."""
    return detection_engine.get_history(page=page, page_size=page_size)
