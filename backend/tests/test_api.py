import io
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.alerts import AlertCreate
from app.services.alert_service import alert_service

client = TestClient(app)


def test_health_endpoint():
    """Verify health endpoint reports API process status."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_readiness_disconnected(disconnected_db):
    """Verify readiness reports degraded (HTTP 503) when database is not connected."""
    res = client.get("/api/ready")
    assert res.status_code == 503
    data = res.json()
    assert data["status"] == "degraded"
    assert data["ready"] is False
    assert data["database"] == "disconnected"


def test_readiness_connected(mock_db):
    """Verify readiness reports ready (HTTP 200) when database is connected."""
    res = client.get("/api/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["ready"] is True
    assert data["database"] == "connected"


def test_event_ingest_and_retrieve(mock_db):
    """Verify single event ingestion and retrieval by ID."""
    event_payload = {
        "id": "EVT-TEST-001",
        "event_type": "auth.login_failed",
        "source_ip": "192.168.1.100",
        "username": "attacker",
        "outcome": "failure",
        "severity": "High",
        "source": "auth-service",
        "description": "Failed password attempt",
        "metadata": {"attempt": 1, "password": "SuperSecretPassword123"},
    }

    # Ingest
    res = client.post("/api/events/ingest", json=event_payload)
    assert res.status_code == 201
    ingest_res = res.json()
    assert ingest_res["created"] == 1
    assert ingest_res["duplicates"] == 0

    # Retrieve by ID
    get_res = client.get("/api/events/EVT-TEST-001")
    assert get_res.status_code == 200
    doc = get_res.json()
    assert doc["id"] == "EVT-TEST-001"
    assert doc["event_type"] == "auth.login_failed"
    assert doc["severity"] == "High"
    # Ensure sensitive key was sanitized
    assert doc["metadata"]["password"] == "[REDACTED]"


def test_invalid_event_payload(mock_db):
    """Verify rejection of invalid event types or bad data."""
    bad_payload = {
        "event_type": "not a valid dot separated type!",
        "severity": "UltraSuperCritical",
    }
    res = client.post("/api/events/ingest", json=bad_payload)
    assert res.status_code == 422


def test_event_pagination_and_filtering(mock_db):
    """Verify pagination and filtering by severity and search term."""
    batch = [
        {"id": f"EVT-B-{i}", "event_type": "api.request", "severity": "Low" if i % 2 == 0 else "Critical", "source": "api-gateway", "description": f"Request {i}"}
        for i in range(10)
    ]
    res = client.post("/api/events/ingest", json=batch)
    assert res.status_code == 201

    # Filter by severity
    crit_res = client.get("/api/events?severity=Critical")
    assert crit_res.status_code == 200
    crit_data = crit_res.json()
    assert crit_data["total"] == 5
    assert len(crit_data["items"]) == 5

    # Pagination: page 2, page_size 3
    page_res = client.get("/api/events?page=2&page_size=3")
    assert page_res.status_code == 200
    page_data = page_res.json()
    assert page_data["page"] == 2
    assert page_data["page_size"] == 3
    assert len(page_data["items"]) == 3


def test_duplicate_event_handling(mock_db):
    """Verify duplicate events with identical IDs are counted as duplicates, not errors."""
    event = {
        "id": "EVT-DUP-999",
        "event_type": "privilege.action",
        "severity": "Medium",
    }
    # First ingest
    res1 = client.post("/api/events/ingest", json=event)
    assert res1.json()["created"] == 1

    # Duplicate ingest
    res2 = client.post("/api/events/ingest", json=event)
    assert res2.json()["created"] == 0
    assert res2.json()["duplicates"] == 1


def test_upload_valid_json_file(mock_db):
    """Verify JSON file upload parsing and ingestion."""
    logs = [
        {"id": "EVT-FILE-1", "event_type": "auth.access_denied", "severity": "High"},
        {"id": "EVT-FILE-2", "event_type": "auth.login_success", "severity": "Info"},
    ]
    file_bytes = json.dumps(logs).encode("utf-8")
    files = {"file": ("test_logs.json", io.BytesIO(file_bytes), "application/json")}

    res = client.post("/api/events/upload", files=files)
    assert res.status_code == 201
    data = res.json()
    assert data["created"] == 2
    assert data["rejected"] == 0


def test_upload_invalid_file_extension(mock_db):
    """Verify rejection of unauthorized file formats (e.g. .exe, .sh)."""
    files = {"file": ("malicious.sh", io.BytesIO(b"echo 'malicious'"), "text/plain")}
    res = client.post("/api/events/upload", files=files)
    assert res.status_code == 201  # returns IngestionResponse with rejection
    data = res.json()
    assert data["created"] == 0
    assert data["rejected"] >= 1
    assert any("Unsupported file format" in err for err in data["errors"])


def test_alert_lifecycle(mock_db):
    """Verify alert listing, retrieval, and status updates with audit logging."""
    # Create an alert
    alert_service.create_alert(
        AlertCreate(
            id="ALT-AUTH-001",
            rule_id="AUTH-001",
            title="Repeated failed logins",
            detail="18 failed attempts from 185.22.14.8",
            severity="Critical",
            matched_count=18,
            event_ids=["EVT-1", "EVT-2"],
        )
    )

    # Fetch alert
    res = client.get("/api/alerts/ALT-AUTH-001")
    assert res.status_code == 200
    alert_data = res.json()
    assert alert_data["status"] == "Open"
    assert alert_data["severity"] == "Critical"

    # Patch alert: update status to Investigating and add notes
    patch_res = client.patch(
        "/api/alerts/ALT-AUTH-001",
        json={"status": "Investigating", "analyst_notes": "Triage started by SOC analyst"},
    )
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["status"] == "Investigating"
    assert updated_data["analyst_notes"] == "Triage started by SOC analyst"

    # Verify audit_log entry was created
    audit_entries = list(mock_db.audit_logs.find({"resource_id": "ALT-AUTH-001"}))
    assert len(audit_entries) >= 1


def test_alert_invalid_status_transition(mock_db):
    """Verify rejection of invalid alert status."""
    res = client.patch(
        "/api/alerts/ALT-NOTFOUND",
        json={"status": "NonExistentStatus"},
    )
    assert res.status_code == 422


def test_incident_creation_and_protection(mock_db):
    """Verify incident creation, protected fields preservation, and update."""
    incident_payload = {
        "title": "Credential Stuffing Campaign",
        "severity": "Critical",
        "description": "Multi-IP authentication brute force attempt against customer portal.",
        "assigned_to": "Alex Morgan",
        "alert_ids": ["ALT-AUTH-001"],
    }
    # Create
    create_res = client.post("/api/incidents", json=incident_payload)
    assert create_res.status_code == 201
    created_inc = create_res.json()
    inc_id = created_inc["id"]
    original_created_at = created_inc["created_at"]
    assert created_inc["status"] == "Open"
    assert created_inc["assigned_to"] == "Alex Morgan"

    # Attempt to patch, ensuring created_at is protected
    patch_res = client.patch(
        f"/api/incidents/{inc_id}",
        json={
            "status": "Contained",
            "resolution_summary": "IPs blocked at perimeter firewall.",
            "created_at": "1999-01-01T00:00:00Z",  # Client cannot overwrite created_at
        },
    )
    assert patch_res.status_code == 200
    updated_inc = patch_res.json()
    assert updated_inc["status"] == "Contained"
    assert updated_inc["resolution_summary"] == "IPs blocked at perimeter firewall."
    assert updated_inc["created_at"] != "1999-01-01T00:00:00Z"
    assert updated_inc["created_at"][:19] == original_created_at[:19]


def test_disconnected_database_graceful_response(disconnected_db):
    """Verify all query endpoints return safe, graceful responses without crashing when DB is offline."""
    events_res = client.get("/api/events")
    assert events_res.status_code == 200
    assert events_res.json()["items"] == []

    alerts_res = client.get("/api/alerts")
    assert alerts_res.status_code == 200
    assert alerts_res.json()["items"] == []

    incidents_res = client.get("/api/incidents")
    assert incidents_res.status_code == 200
    assert incidents_res.json()["items"] == []
