"""
Authentication routes for admin login.
"""

from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Response, Request, Depends
from sqlalchemy.orm import Session

from app.schemas import LoginRequest, Token
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


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    if not authenticate_admin(login_data.username, login_data.password):
        logger.warning(f"Failed login attempt for user: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    access_token = create_access_token(
        data={"sub": login_data.username},
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
        admin_user=login_data.username,
        action="login",
        resource_type="session",
        ip_address=get_client_ip(request)
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Admin login successful: {login_data.username}")
    return Token(access_token=access_token)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    response.delete_cookie("access_token")

    audit_log = AuditLog(
        admin_user=current_user,
        action="logout",
        resource_type="session",
        ip_address=get_client_ip(request)
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Admin logout: {current_user}")
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_admin(current_user: str = Depends(get_current_user)):
    return {"username": current_user}
