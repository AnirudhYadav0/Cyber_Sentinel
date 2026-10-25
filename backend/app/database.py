import logging
from typing import Optional
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.errors import PyMongoError, ConnectionFailure, ServerSelectionTimeoutError
from app.config import settings

logger = logging.getLogger("cybersentinel.database")


class DatabaseManager:
    """Managed MongoDB client and database connection lifecycle handler."""

    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self._connected: bool = False

    def connect(self) -> bool:
        """Connect to MongoDB Atlas or configured MongoDB instance."""
        uri = settings.mongodb_uri

        # Check if URI is unconfigured or a placeholder
        if not uri or uri == "mongodb_connection_string_placeholder" or "placeholder" in uri:
            logger.info("MongoDB URI is not configured (using placeholder). Database features will be in disconnected mode.")
            self._connected = False
            return False

        try:
            logger.info(f"Connecting to MongoDB database: {settings.mongodb_database}...")
            self.client = MongoClient(
                uri,
                serverSelectionTimeoutMS=settings.mongodb_timeout_ms,
                connectTimeoutMS=settings.mongodb_timeout_ms,
                retryWrites=True,
            )
            # Verify connectivity with an admin ping
            self.client.admin.command("ping")
            self.db = self.client[settings.mongodb_database]
            self._connected = True
            logger.info(f"Successfully connected and verified MongoDB database '{settings.mongodb_database}'.")
            self.ensure_indexes()
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError, PyMongoError) as err:
            logger.warning(f"MongoDB connection failed: {err.__class__.__name__}. Application will run in degraded mode.")
            self.client = None
            self.db = None
            self._connected = False
            return False
        except Exception as ex:
            logger.warning(f"Unexpected error connecting to MongoDB: {ex.__class__.__name__}.")
            self.client = None
            self.db = None
            self._connected = False
            return False

    def disconnect(self):
        """Cleanly close database client connection."""
        if self.client:
            try:
                self.client.close()
                logger.info("MongoDB client connection closed cleanly.")
            except Exception as err:
                logger.error(f"Error closing MongoDB client: {err.__class__.__name__}")
            finally:
                self.client = None
                self.db = None
                self._connected = False

    def ping(self) -> bool:
        """Check if active database connection is alive."""
        if not self._connected or self.client is None or self.db is None:
            return False
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            self._connected = False
            return False

    def is_connected(self) -> bool:
        """Report connection status without raising exceptions."""
        return self._connected and self.db is not None

    def get_database(self) -> Optional[Database]:
        """Return the current database instance."""
        return self.db

    def set_database(self, db: Optional[Database]):
        """Inject database instance (useful for unit tests or mocked environments)."""
        self.db = db
        self._connected = db is not None
        if self._connected:
            self.ensure_indexes()

    def ensure_indexes(self):
        """Create required indexes across collections."""
        if self.db is None:
            return

        try:
            # 1. security_events indexes
            self.db.security_events.create_index([("id", ASCENDING)], unique=True, sparse=True)
            self.db.security_events.create_index([("timestamp", DESCENDING)])
            self.db.security_events.create_index([("event_type", ASCENDING)])
            self.db.security_events.create_index([("severity", ASCENDING)])
            self.db.security_events.create_index([("outcome", ASCENDING)])
            self.db.security_events.create_index([("source_ip", ASCENDING)])

            # 2. alerts indexes
            self.db.alerts.create_index([("id", ASCENDING)], unique=True, sparse=True)
            self.db.alerts.create_index([("dedup_key", ASCENDING)], sparse=True)
            self.db.alerts.create_index([("timestamp", DESCENDING)])
            self.db.alerts.create_index([("severity", ASCENDING)])
            self.db.alerts.create_index([("status", ASCENDING)])
            self.db.alerts.create_index([("rule_id", ASCENDING)])

            # 3. incidents indexes
            self.db.incidents.create_index([("id", ASCENDING)], unique=True, sparse=True)
            self.db.incidents.create_index([("created_at", DESCENDING)])
            self.db.incidents.create_index([("severity", ASCENDING)])
            self.db.incidents.create_index([("status", ASCENDING)])

            # 4. users indexes
            self.db.users.create_index([("username", ASCENDING)], unique=True, sparse=True)
            self.db.users.create_index([("email", ASCENDING)], unique=True, sparse=True)

            # 5. audit_logs indexes
            self.db.audit_logs.create_index([("timestamp", DESCENDING)])
            self.db.audit_logs.create_index([("action", ASCENDING)])
            self.db.audit_logs.create_index([("resource_type", ASCENDING)])

            # 6. detection_history indexes
            self.db.detection_history.create_index([("timestamp", DESCENDING)])

            logger.info("Verified all MongoDB collection indexes.")
        except Exception as err:
            logger.warning(f"Could not initialize collection indexes: {err.__class__.__name__}")


db_manager = DatabaseManager()


def get_db() -> Optional[Database]:
    """Dependency helper to get the database."""
    return db_manager.get_database()
