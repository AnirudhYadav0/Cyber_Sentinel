from datetime import datetime, timezone, timedelta
import logging
import uuid
from typing import Optional, List, Dict, Any
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

from app.config import settings
from app.database import db_manager
from app.schemas.auth import UserResponse, UserRegister, TokenPayload

logger = logging.getLogger("cybersentinel.auth")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# In-memory fallback users for disconnected or testing environments
_FALLBACK_USERS: Dict[str, Dict[str, Any]] = {}


def hash_password(password: str) -> str:
    """Hash password using bcrypt with salt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as err:
        logger.warning(f"Error during password verification: {err.__class__.__name__}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access",
    })
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and validate JWT access token signature and expiration."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(err)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthService:
    """Authentication and user access management service."""

    def __init__(self):
        self._ensure_fallback_users()

    def _ensure_fallback_users(self):
        """Initialize in-memory users for offline/mock test environments."""
        global _FALLBACK_USERS
        if not _FALLBACK_USERS:
            now = datetime.now(timezone.utc)
            _FALLBACK_USERS = {
                settings.admin_default_username: {
                    "id": "USR-ADMIN-001",
                    "username": settings.admin_default_username,
                    "email": "admin@cybersentinel.local",
                    "password_hash": hash_password(settings.admin_default_password),
                    "role": "admin",
                    "is_active": True,
                    "created_at": now,
                },
                settings.analyst_default_username: {
                    "id": "USR-ANALYST-001",
                    "username": settings.analyst_default_username,
                    "email": "analyst@cybersentinel.local",
                    "password_hash": hash_password(settings.analyst_default_password),
                    "role": "analyst",
                    "is_active": True,
                    "created_at": now,
                },
            }

    def seed_default_users(self, db):
        """Seed default admin and analyst users into MongoDB users collection if not present."""
        if db is None:
            return

        self._ensure_fallback_users()
        try:
            for username, user_data in _FALLBACK_USERS.items():
                existing = db.users.find_one({"username": username})
                if not existing:
                    db.users.insert_one(user_data.copy())
                    logger.info(f"Seeded default security user: '{username}' with role '{user_data['role']}'.")
        except Exception as err:
            logger.warning(f"Could not seed default users into MongoDB: {err.__class__.__name__}")

    def get_user_by_username(self, username: str) -> Optional[dict]:
        """Fetch user record by username from DB or fallback store."""
        db = db_manager.get_database()
        if db is not None:
            try:
                user = db.users.find_one({"username": username.lower()})
                if user:
                    return user
            except Exception as err:
                logger.warning(f"Error querying user {username}: {err.__class__.__name__}")

        # Check fallback
        self._ensure_fallback_users()
        return _FALLBACK_USERS.get(username.lower())

    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user by username and password."""
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not user.get("is_active", True):
            return None
        if not verify_password(password, user.get("password_hash", "")):
            return None
        return user

    def register_user(self, payload: UserRegister) -> UserResponse:
        """Register a new user in the system."""
        db = db_manager.get_database()
        username = payload.username.lower()

        # Check duplicate
        if self.get_user_by_username(username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with username '{username}' already exists.",
            )

        now = datetime.now(timezone.utc)
        user_id = f"USR-{uuid.uuid4().hex[:8].upper()}"
        doc = {
            "id": user_id,
            "username": username,
            "email": payload.email.lower(),
            "password_hash": hash_password(payload.password),
            "role": payload.role.lower(),
            "is_active": True,
            "created_at": now,
        }

        if db is not None:
            try:
                db.users.insert_one(doc)
            except Exception as err:
                logger.error(f"Failed to persist user {username}: {err.__class__.__name__}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database error creating user.",
                )
        else:
            _FALLBACK_USERS[username] = doc

        return UserResponse(
            id=user_id,
            username=username,
            email=payload.email.lower(),
            role=payload.role.lower(),
            is_active=True,
            created_at=now,
        )


auth_service = AuthService()


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
) -> UserResponse:
    """
    FastAPI dependency: resolves the authenticated user from the Bearer token.
    Enforces strict token validation when token is passed.
    When token is absent in non-production development/demo mode, provides a default analyst identity.
    In production mode, token is strictly required.
    """
    if token:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is missing subject identifier.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_doc = auth_service.get_user_by_username(username)
        if not user_doc or not user_doc.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account does not exist or has been deactivated.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return UserResponse(
            id=user_doc.get("id", f"USR-{username}"),
            username=user_doc["username"],
            email=user_doc.get("email", f"{username}@cybersentinel.local"),
            role=user_doc.get("role", "analyst"),
            is_active=user_doc.get("is_active", True),
            created_at=user_doc.get("created_at", datetime.now(timezone.utc)),
        )

    # No token provided
    if settings.app_env.lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Non-production demo fallback
    return UserResponse(
        id="USR-DEMO-ANALYST",
        username=settings.analyst_default_username,
        email="analyst@cybersentinel.local",
        role="analyst",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


async def get_strict_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
) -> UserResponse:
    """Strictly require token regardless of environment (for /me, user creation, etc.)."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await get_current_user(token)


def require_role(allowed_roles: List[str]):
    """Role-based access control dependency factory."""
    async def role_checker(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if current_user.role not in allowed_roles:
            logger.warning(
                f"Unauthorized access attempt by user '{current_user.username}' with role '{current_user.role}' (allowed: {allowed_roles})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: this operation requires one of the following roles: {', '.join(allowed_roles)}.",
            )
        return current_user
    return role_checker


# Convenient role dependencies
require_admin = require_role(["admin"])
require_analyst = require_role(["admin", "analyst"])
