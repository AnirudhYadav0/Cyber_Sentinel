"""Database connection manager placeholder for CyberSentinel.

MongoDB Atlas integration will be implemented in subsequent phases.
"""

from typing import Optional


class DatabaseManager:
    client = None
    db = None

    @classmethod
    def get_database(cls):
        return cls.db

    @classmethod
    def is_connected(cls) -> bool:
        return cls.client is not None and cls.db is not None


db_manager = DatabaseManager()
