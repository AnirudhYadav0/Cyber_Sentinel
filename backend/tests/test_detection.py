from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.detection.engine import detection_engine
from app.detection.schemas import RuleUpdate
from app.services.event_service import event_service
from app.schemas.events import SecurityEventCreate

client = TestClient(app)


def test_empty_dataset(mock_db):
    """Verify detection run against empty database yields 0 detections cleanly."""
    res = client.post("/api/detection/run", json={"lookback_minutes": 60})
    assert res.status_code == 200
    data = res.json()
    assert data["events_examined"] == 0
    assert data["detections_generated"] == 0
    assert data["alerts_created"] == 0


def test_failed_logins_below_threshold(mock_db):
    """AUTH-001: 3 failed attempts (threshold is 5) should NOT trigger detection."""
    now = datetime.now(timezone.utc)
    events = [
        SecurityEventCreate(
            id=f"EVT-FL-B-{i}",
            event_type="auth.login_failed",
            source_ip="10.0.0.5",
            username="target_user",
            outcome="failure",
            timestamp=now - timedelta(minutes=2),
        )
        for i in range(3)
    ]
    event_service.ingest_events(events)

    res = client.post("/api/detection/run", json={"lookback_minutes": 30, "rule_ids": ["AUTH-001"]})
    assert res.status_code == 200
    data = res.json()
    assert data["events_examined"] == 3
    assert data["detections_generated"] == 0
    assert data["alerts_created"] == 0


def test_failed_logins_above_threshold(mock_db):
    """AUTH-001: 6 failed attempts (threshold is 5) SHOULD trigger detection and create alert."""
    now = datetime.now(timezone.utc)
    events = [
        SecurityEventCreate(
            id=f"EVT-FL-A-{i}",
            event_type="auth.login_failed",
            source_ip="198.51.100.22",
            username="admin",
            outcome="failure",
            timestamp=now - timedelta(minutes=1),
        )
        for i in range(6)
    ]
    event_service.ingest_events(events)

    res = client.post("/api/detection/run", json={"lookback_minutes": 30, "rule_ids": ["AUTH-001"]})
    assert res.status_code == 200
    data = res.json()
    assert data["detections_generated"] == 1
    assert data["alerts_created"] == 1

    det = data["detections"][0]
    assert det["rule_id"] == "AUTH-001"
    assert det["source_identifier"] == "198.51.100.22"
    assert det["matched_event_count"] == 6

    # Verify alert exists in database
    alert_doc = mock_db.alerts.find_one({"rule_id": "AUTH-001"})
    assert alert_doc is not None
    assert alert_doc["matched_count"] == 6


def test_events_outside_time_window(mock_db):
    """Events occurring outside the rule's time window should not count toward threshold."""
    now = datetime.now(timezone.utc)
    # 6 failed events from 45 minutes ago (outside AUTH-001 10-minute window)
    events = [
        SecurityEventCreate(
            id=f"EVT-OLD-{i}",
            event_type="auth.login_failed",
            source_ip="10.10.10.10",
            outcome="failure",
            timestamp=now - timedelta(minutes=45),
        )
        for i in range(6)
    ]
    event_service.ingest_events(events)

    res = client.post("/api/detection/run", json={"lookback_minutes": 60, "rule_ids": ["AUTH-001"]})
    assert res.status_code == 200
    data = res.json()
    assert data["detections_generated"] == 0


def test_repeated_unauthorized_access(mock_db):
    """AUTH-002: Repeated 401/403 access_denied events exceed threshold."""
    now = datetime.now(timezone.utc)
    events = [
        SecurityEventCreate(
            id=f"EVT-DENIED-{i}",
            event_type="auth.access_denied",
            source_ip="203.0.113.5",
            outcome="denied",
            timestamp=now - timedelta(minutes=3),
        )
        for i in range(5)
    ]
    event_service.ingest_events(events)

    res = client.post("/api/detection/run", json={"lookback_minutes": 30, "rule_ids": ["AUTH-002"]})
    assert res.status_code == 200
    data = res.json()
    assert data["detections_generated"] == 1
    assert data["detections"][0]["rule_id"] == "AUTH-002"


def test_high_request_volume(mock_db):
    """TRAFFIC-001: 32 requests in 5 minutes trigger volume anomaly alert."""
    now = datetime.now(timezone.utc)
    events = [
        SecurityEventCreate(
            id=f"EVT-REQ-{i}",
            event_type="api.request",
            source_ip="192.0.2.88",
            source="edge-gateway",
            timestamp=now - timedelta(minutes=1),
        )
        for i in range(32)
    ]
    event_service.ingest_events(events)

    res = client.post("/api/detection/run", json={"lookback_minutes": 30, "rule_ids": ["TRAFFIC-001"]})
    assert res.status_code == 200
    data = res.json()
    assert data["detections_generated"] == 1
    assert data["detections"][0]["rule_id"] == "TRAFFIC-001"


def test_privileged_action_policy(mock_db):
    """PRIV-001: Expected action is allowed, unexpected action generates alert."""
    now = datetime.now(timezone.utc)
    # 1. Allowed action
    allowed_evt = SecurityEventCreate(
        id="EVT-PRIV-ALLOWED",
        event_type="privilege.action",
        username="lead_admin",
        description="read_config",
        metadata={"action": "read_config"},
        timestamp=now - timedelta(minutes=5),
    )
    # 2. Unexpected action
    unexpected_evt = SecurityEventCreate(
        id="EVT-PRIV-ROGUE",
        event_type="privilege.action",
        username="intern_bob",
        description="purge_production_backups",
        metadata={"action": "purge_production_backups"},
        timestamp=now - timedelta(minutes=2),
    )
    event_service.ingest_events([allowed_evt, unexpected_evt])

    res = client.post("/api/detection/run", json={"lookback_minutes": 30, "rule_ids": ["PRIV-001"]})
    assert res.status_code == 200
    data = res.json()
    assert data["detections_generated"] == 1
    det = data["detections"][0]
    assert det["rule_id"] == "PRIV-001"
    assert det["source_identifier"] == "intern_bob"


def test_disabled_rule(mock_db):
    """Disabled rules are excluded from evaluation."""
    # Temporarily disable AUTH-001
    detection_engine.update_rule_config("AUTH-001", RuleUpdate(enabled=False))

    now = datetime.now(timezone.utc)
    events = [
        SecurityEventCreate(
            id=f"EVT-DIS-{i}",
            event_type="auth.login_failed",
            source_ip="10.0.0.99",
            outcome="failure",
            timestamp=now - timedelta(minutes=1),
        )
        for i in range(10)
    ]
    event_service.ingest_events(events)

    res = client.post("/api/detection/run", json={"lookback_minutes": 30, "rule_ids": ["AUTH-001"]})
    assert res.status_code == 200
    data = res.json()
    assert data["rules_evaluated"] == 0
    assert data["detections_generated"] == 0

    # Re-enable rule
    detection_engine.update_rule_config("AUTH-001", RuleUpdate(enabled=True))


def test_alert_deduplication_and_status_preservation(mock_db):
    """Verify second detection run does not create duplicate alert and preserves Resolved status."""
    now = datetime.now(timezone.utc)
    events = [
        SecurityEventCreate(
            id=f"EVT-DEDUP-{i}",
            event_type="auth.login_failed",
            source_ip="185.220.101.5",
            outcome="failure",
            timestamp=now - timedelta(minutes=1),
        )
        for i in range(6)
    ]
    event_service.ingest_events(events)

    # Run 1: Should create 1 alert
    res1 = client.post("/api/detection/run", json={"lookback_minutes": 30, "rule_ids": ["AUTH-001"]})
    assert res1.json()["alerts_created"] == 1
    assert res1.json()["alerts_deduplicated"] == 0

    # Triage the created alert to Resolved
    alert_doc = mock_db.alerts.find_one({"rule_id": "AUTH-001"})
    assert alert_doc is not None
    client.patch(f"/api/alerts/{alert_doc['id']}", json={"status": "Resolved", "analyst_notes": "Handled"})

    # Run 2: Same time bucket and source -> Should detect duplicate and NOT overwrite Resolved status
    res2 = client.post("/api/detection/run", json={"lookback_minutes": 30, "rule_ids": ["AUTH-001"]})
    assert res2.json()["alerts_created"] == 0
    assert res2.json()["alerts_deduplicated"] == 1

    # Verify status is still Resolved in DB
    refreshed_alert = mock_db.alerts.find_one({"id": alert_doc["id"]})
    assert refreshed_alert["status"] == "Resolved"
    assert refreshed_alert["analyst_notes"] == "Handled"


def test_disconnected_db_handling(disconnected_db):
    """Verify detection run returns safe response without crashing when database is offline."""
    res = client.post("/api/detection/run", json={"lookback_minutes": 30})
    assert res.status_code == 200
    data = res.json()
    assert data["events_examined"] == 0
    assert data["detections_generated"] == 0


def test_rule_tuning_and_validation(admin_headers, analyst_headers):
    """Verify rule update endpoint RBAC and parameter validation."""
    # 1. Non-admin analyst role is forbidden (HTTP 403)
    forbidden_res = client.patch(
        "/api/detection/rules/AUTH-001",
        json={"threshold": 8},
        headers=analyst_headers,
    )
    assert forbidden_res.status_code == 403
    assert "Forbidden" in forbidden_res.json()["detail"]

    # 2. Administrator role succeeds (HTTP 200)
    patch_res = client.patch(
        "/api/detection/rules/AUTH-001",
        json={"threshold": 8, "window_minutes": 15, "severity": "High"},
        headers=admin_headers,
    )
    assert patch_res.status_code == 200
    rule = patch_res.json()
    assert rule["threshold"] == 8
    assert rule["window_minutes"] == 15
    assert rule["severity"] == "High"

    # 3. Invalid threshold (0 is not allowed)
    bad_res = client.patch(
        "/api/detection/rules/AUTH-001",
        json={"threshold": 0},
        headers=admin_headers,
    )
    assert bad_res.status_code == 422

    # 4. Reset back to default
    client.patch(
        "/api/detection/rules/AUTH-001",
        json={"threshold": 5, "window_minutes": 10, "severity": "Critical"},
        headers=admin_headers,
    )


def test_detection_history_retrieval(mock_db):
    """Verify detection history endpoint lists recorded detection runs."""
    # Execute a run
    client.post("/api/detection/run", json={"lookback_minutes": 15})

    hist_res = client.get("/api/detection/history")
    assert hist_res.status_code == 200
    data = hist_res.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert "run_id" in data["items"][0]
