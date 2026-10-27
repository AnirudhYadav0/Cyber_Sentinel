import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.config import settings
from app.schemas.auth import UserLogin, UserRegister, UserResponse, TokenResponse
from app.security.authentication import (
    auth_service,
    create_access_token,
    get_strict_current_user,
    require_admin,
)
from app.security.rate_limiter import rate_limit_dependency, get_client_ip
from app.services.audit_service import audit_service

logger = logging.getLogger("cybersentinel.auth.routes")

router = APIRouter(prefix="/api/auth", tags=["Authentication & Access Control"])


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_dependency("auth_login", max_requests=settings.auth_rate_limit_per_minute, window_seconds=60))],
)
def login(payload: UserLogin, request: Request):
    """
    Authenticate security analyst or administrator credentials.
    Issues a cryptographically signed JWT access token upon successful authentication.
    Rate limited against brute-force attacks.
    """
    client_ip = get_client_ip(request)
    user = auth_service.authenticate_user(payload.username, payload.password)
    if not user:
        # Audit log failed authentication without recording the attempted password
        audit_service.log_action(
            action="auth_failure",
            resource_type="auth",
            resource_id=payload.username,
            user="anonymous",
            changes={"client_ip": client_ip, "reason": "invalid_credentials"},
        )
        logger.warning(f"Failed authentication attempt for username '{payload.username}' from IP {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Authentication succeeded
    expires_minutes = settings.access_token_expire_minutes
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=timedelta(minutes=expires_minutes),
    )

    audit_service.log_action(
        action="auth_success",
        resource_type="auth",
        resource_id=user["username"],
        user=user["username"],
        changes={"client_ip": client_ip, "role": user["role"]},
    )
    logger.info(f"User '{user['username']}' ({user['role']}) authenticated successfully from IP {client_ip}")

    user_resp = UserResponse(
        id=user.get("id", f"USR-{user['username']}"),
        username=user["username"],
        email=user.get("email", f"{user['username']}@cybersentinel.local"),
        role=user["role"],
        is_active=user.get("is_active", True),
        created_at=user.get("created_at"),
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_minutes * 60,
        user=user_resp,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: UserResponse = Depends(get_strict_current_user),
):
    """Retrieve profile and permissions for the currently authenticated session."""
    return current_user


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def register_user(
    payload: UserRegister,
    admin_user: UserResponse = Depends(require_admin),
):
    """
    Provision a new analyst or administrator account.
    Restricted to administrator role only.
    """
    created_user = auth_service.register_user(payload)
    audit_service.log_action(
        action="create_user",
        resource_type="user",
        resource_id=created_user.id,
        user=admin_user.username,
        changes={"username": created_user.username, "role": created_user.role},
    )
    logger.info(f"Admin '{admin_user.username}' created new user '{created_user.username}' with role '{created_user.role}'")
    return created_user


@router.post("/logout")
def logout(current_user: UserResponse = Depends(get_strict_current_user)):
    """Acknowledge session termination and logout."""
    audit_service.log_action(
        action="logout",
        resource_type="auth",
        resource_id=current_user.username,
        user=current_user.username,
    )
    return {"message": "Session terminated successfully."}
