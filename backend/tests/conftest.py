import pytest
import mongomock
from app.database import db_manager


@pytest.fixture
def mock_db():
    """Provide an in-memory mock MongoDB database for testing."""
    mock_client = mongomock.MongoClient()
    test_db = mock_client["cybersentinel_test"]
    # Provide ping command support on admin database
    mock_client.admin.command = lambda cmd, *args, **kwargs: {"ok": 1.0}
    db_manager.client = mock_client
    db_manager.set_database(test_db)
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
