import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify health endpoint returns healthy status and metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data
    assert "timestamp" in data


def test_ready_endpoint_reports_real_state():
    """Verify readiness endpoint accurately reports disconnected DB when not connected."""
    response = client.get("/api/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["database"] == "disconnected"
    assert data["ready"] is False


def test_events_endpoint_returns_empty_in_phase1():
    """Verify /api/events returns empty events list without synthetic/mock injection."""
    response = client.get("/api/events")
    assert response.status_code == 200
    data = response.json()
    assert data["events"] == []
    assert data["total"] == 0


def test_cors_headers():
    """Verify CORS middleware allows requests from localhost:3000."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
