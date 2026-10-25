from datetime import datetime, timezone
import logging
from typing import Optional, Dict, Any
from app.database import db_manager

logger = logging.getLogger("cybersentinel.audit")


class AuditService:
    @staticmethod
    def log_action(
        action: str,
        resource_type: str,
        resource_id: str,
        user: Optional[str] = "system",
        changes: Optional[Dict[str, Any]] = None,
    ):
        """Record an action in the audit_logs collection."""
        db = db_manager.get_database()
        entry = {
            "timestamp": datetime.now(timezone.utc),
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user": user or "anonymous",
            "changes": changes or {},
        }
        if db is not None:
            try:
                db.audit_logs.insert_one(entry)
            except Exception as err:
                logger.warning(f"Failed to record audit log: {err.__class__.__name__}")
        else:
            logger.debug(f"Audit log (unconnected db): {entry}")


audit_service = AuditService()
