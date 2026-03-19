"""
Authentication routes for admin login.
"""

from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Response, Request, Depends
from sqlalchemy.orm import Session

from app.schemas import LoginRequest, Token, LoginResponse
from app.config import get_settings
from app.database import get_db
from app.models import AuditLog
from app.utils.security import (
    authenticate_admin,
    create_access_token,
    get_current_user,
    get_client_ip
)
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
settings = get_settings()
logger = get_logger()


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    admin_data = authenticate_admin(login_data.username, login_data.password, db)

    if not admin_data:
        logger.warning(f"Failed login attempt for user: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    access_token = create_access_token(
        data={
            "sub": admin_data["username"],
            "role": admin_data["role"]
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )

    audit_log = AuditLog(
        admin_user=admin_data["username"],
        action="login",
        resource_type="session",
        ip_address=get_client_ip(request),
        details={"role": admin_data["role"]}
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Admin login successful: {admin_data['username']} ({admin_data['role']})")
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        role=admin_data["role"],
        username=admin_data["username"],
        full_name=admin_data.get("full_name")
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    response.delete_cookie("access_token")

    audit_log = AuditLog(
        admin_user=current_user["username"],
        action="logout",
        resource_type="session",
        ip_address=get_client_ip(request)
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Admin logout: {current_user['username']}")
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_admin(current_user: dict = Depends(get_current_user)):
    return current_user
