from datetime import timedelta
import pytest
import mongomock
from app.database import db_manager
from app.config import settings
from app.security.authentication import create_access_token, auth_service
from app.security.rate_limiter import limiter


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset rate limiter state before each test run."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def mock_db():
    """Provide an in-memory mock MongoDB database for testing."""
    mock_client = mongomock.MongoClient()
    test_db = mock_client["cybersentinel_test"]
    # Provide ping command support on admin database
    mock_client.admin.command = lambda cmd, *args, **kwargs: {"ok": 1.0}
    db_manager.client = mock_client
    db_manager.set_database(test_db)
    # Seed default test users
    auth_service.seed_default_users(test_db)
    yield test_db
    # Cleanup after test
    mock_client.close()
    db_manager.set_database(None)
    db_manager.client = None


@pytest.fixture
def disconnected_db():
    """Ensure db_manager reports disconnected state for testing failure handling."""
    original_client = db_manager.client
    original_db = db_manager.db
    db_manager.client = None
    db_manager.set_database(None)
    yield
    db_manager.client = original_client
    db_manager.set_database(original_db)


@pytest.fixture
def admin_token():
    """Generate a valid JWT token for an administrator."""
    return create_access_token(
        data={"sub": settings.admin_default_username, "role": "admin"},
        expires_delta=timedelta(minutes=30),
    )


@pytest.fixture
def admin_headers(admin_token):
    """Authorization headers for an administrator."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def analyst_token():
    """Generate a valid JWT token for a security analyst."""
    return create_access_token(
        data={"sub": settings.analyst_default_username, "role": "analyst"},
        expires_delta=timedelta(minutes=30),
    )


@pytest.fixture
def analyst_headers(analyst_token):
    """Authorization headers for a security analyst."""
    return {"Authorization": f"Bearer {analyst_token}"}
