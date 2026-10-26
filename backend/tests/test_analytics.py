from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.services.event_service import event_service
from app.schemas.events import SecurityEventCreate
from app.services.alert_service import alert_service
from app.schemas.alerts import AlertCreate

client = TestClient(app)


def test_analytics_disconnected(disconnected_db):
    """Verify analytics endpoints return safe zero/empty responses when DB is disconnected."""
    res = client.get("/api/analytics/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_events"] == 0
    assert data["active_alerts"] == 0
    assert data["open_incidents"] == 0
    assert "detection_coverage_pct" in data

    res_trends = client.get("/api/analytics/trends?range=24h")
    assert res_trends.status_code == 200
    trends_data = res_trends.json()
    assert trends_data["total_in_period"] == 0
    assert len(trends_data["points"]) == 7

    res_sev = client.get("/api/analytics/severity")
    assert res_sev.status_code == 200
    sev_data = res_sev.json()
    assert sev_data["total_alerts"] == 0
    assert sev_data["total_events"] == 0

    res_src = client.get("/api/analytics/sources?range=7d")
    assert res_src.status_code == 200
    assert res_src.json()["total"] == 0


def test_analytics_with_data(mock_db):
    """Verify analytics summary, trends, and severity calculation with live records."""
    now = datetime.now(timezone.utc)
    # Ingest events
    events = [
        SecurityEventCreate(
            id="EVT-AN-1",
            event_type="auth.login_failed",
            severity="Critical",
            source="auth-service",
            timestamp=now - timedelta(hours=1),
        ),
        SecurityEventCreate(
            id="EVT-AN-2",
            event_type="api.request",
            severity="Medium",
            source="api-gateway",
            timestamp=now - timedelta(hours=2),
        ),
    ]
    event_service.ingest_events(events)

    # Ingest alert
    alert_service.create_alert(
        AlertCreate(
            id="ALT-AN-1",
            rule_id="AUTH-001",
            title="Brute force test",
            severity="Critical",
            status="Open",
            matched_count=5,
        )
    )

    # Check summary
    res = client.get("/api/analytics/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_events"] == 2
    assert data["active_alerts"] == 1
    assert data["rules_triggered"] >= 1

    # Check trends
    res_trends = client.get("/api/analytics/trends?range=24h")
    assert res_trends.status_code == 200
    assert res_trends.json()["total_in_period"] == 2

    # Check severity
    res_sev = client.get("/api/analytics/severity")
    assert res_sev.status_code == 200
    sev_data = res_sev.json()
    assert sev_data["total_alerts"] == 1
    assert sev_data["alerts_by_severity"]["Critical"] == 1
    assert sev_data["events_by_severity"]["Critical"] == 1
    assert sev_data["events_by_severity"]["Medium"] == 1
