"""
Admin user management routes (for creating HR and Attendance accounts).
"""

from typing import List
from fastapi import APIRouter, HTTPException, status, Request, Depends
from sqlalchemy.orm import Session

from app.schemas import AdminUserCreate, AdminUserUpdate, AdminUserResponse
from app.database import get_db
from app.models import AdminUser, AuditLog
from app.utils.security import get_current_user, require_role, get_password_hash, get_client_ip
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/admin-users", tags=["Admin Users"])
logger = get_logger()


@router.get("", response_model=List[AdminUserResponse])
async def list_admin_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin"))
):
    users = db.query(AdminUser).order_by(AdminUser.created_at.desc()).all()
    return users


@router.post("", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    request: Request,
    user_data: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin"))
):
    existing = db.query(AdminUser).filter(AdminUser.username == user_data.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    new_user = AdminUser(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    audit_log = AuditLog(
        admin_user=current_user["username"],
        action="create_admin_user",
        resource_type="admin_user",
        resource_id=new_user.id,
        details={"username": new_user.username, "role": new_user.role},
        ip_address=get_client_ip(request)
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Admin user created: {new_user.username} ({new_user.role}) by {current_user['username']}")
    return new_user


@router.put("/{user_id}", response_model=AdminUserResponse)
async def update_admin_user(
    request: Request,
    user_id: str,
    user_data: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin"))
):
    admin_user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found"
        )

    if user_data.full_name is not None:
        admin_user.full_name = user_data.full_name
    if user_data.password is not None:
        admin_user.password_hash = get_password_hash(user_data.password)
    if user_data.role is not None:
        admin_user.role = user_data.role
    if user_data.is_active is not None:
        admin_user.is_active = user_data.is_active

    db.commit()
    db.refresh(admin_user)

    audit_log = AuditLog(
        admin_user=current_user["username"],
        action="update_admin_user",
        resource_type="admin_user",
        resource_id=admin_user.id,
        details={"username": admin_user.username, "updates": user_data.dict(exclude_unset=True, exclude={"password"})},
        ip_address=get_client_ip(request)
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Admin user updated: {admin_user.username} by {current_user['username']}")
    return admin_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_user(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin"))
):
    admin_user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found"
        )

    if admin_user.username == current_user["username"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    username = admin_user.username
    db.delete(admin_user)

    audit_log = AuditLog(
        admin_user=current_user["username"],
        action="delete_admin_user",
        resource_type="admin_user",
        resource_id=user_id,
        details={"username": username},
        ip_address=get_client_ip(request)
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Admin user deleted: {username} by {current_user['username']}")
    return None
