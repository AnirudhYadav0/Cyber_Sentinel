from typing import Optional
from fastapi import APIRouter, Query

from app.schemas.analytics import (
    DashboardSummary,
    TrendsResponse,
    SeverityResponse,
    SourceDistributionResponse,
)
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Reporting"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary():
    """Retrieve high-level KPI metrics for events, alerts, and incident posture."""
    return analytics_service.get_summary()


@router.get("/trends", response_model=TrendsResponse)
def get_event_trends(
    range_param: str = Query(default="24h", alias="range", pattern="^(24h|7d|30d)$")
):
    """Retrieve chronological event volume trends across specified time horizon."""
    return analytics_service.get_trends(range_str=range_param)


@router.get("/severity", response_model=SeverityResponse)
def get_severity_breakdown():
    """Retrieve severity distribution for alerts and events."""
    return analytics_service.get_severity()


@router.get("/sources", response_model=SourceDistributionResponse)
def get_event_sources(
    range_param: str = Query(default="7d", alias="range", pattern="^(24h|7d|30d)$")
):
    """Retrieve breakdown of events by originating source."""
    return analytics_service.get_sources(range_str=range_param)
