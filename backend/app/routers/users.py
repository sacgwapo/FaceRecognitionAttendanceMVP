"""
User management routes.
"""

import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import User, AuditLog
from app.schemas import UserCreate, UserUpdate, UserResponse, FaceRegistrationResult
from app.services.face_recognition_service import get_face_service
from app.utils.security import get_current_user, get_client_ip, require_role
from app.utils.logging import get_logger
from app.config import get_settings

router = APIRouter(prefix="/api/users", tags=["Users"])
logger = get_logger()
settings = get_settings()


@router.get("", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "hr"))
):
    query = db.query(User)

    if search:
        query = query.filter(
            (User.name.ilike(f"%{search}%")) |
            (User.employee_id.ilike(f"%{search}%")) |
            (User.department.ilike(f"%{search}%"))
        )

    if active_only:
        query = query.filter(User.is_active == True)

    users = query.order_by(User.name).offset(skip).limit(limit).all()
    return users


@router.get("/stats")
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "hr"))
):
    total = db.query(func.count(User.id)).scalar()
    active = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    registered_faces = db.query(func.count(User.id)).filter(User.face_registered == True).scalar()

    return {
        "total_users": total or 0,
        "active_users": active or 0,
        "registered_faces": registered_faces or 0
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "hr"))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin"))
):
    existing = db.query(User).filter(User.employee_id == user_data.employee_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this employee ID already exists"
        )

    user = User(**user_data.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)

    audit_log = AuditLog(
        admin_user=current_user["username"],
        action="create_user",
        resource_type="user",
        resource_id=user.id,
        details={"employee_id": user.employee_id, "name": user.name},
        ip_address=get_client_ip(request)
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"User created: {user.employee_id} - {user.name}")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin"))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    audit_log = AuditLog(
        admin_user=current_user["username"],
        action="update_user",
        resource_type="user",
        resource_id=user.id,
        details={"updated_fields": list(update_data.keys())},
        ip_address=get_client_ip(request)
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"User updated: {user.employee_id}")
    return user


@router.delete("/{user_id}")
async def delete_user(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin"))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    employee_id = user.employee_id
    name = user.name

    if user.face_image_path:
        image_path = Path(user.face_image_path)
        if image_path.exists():
            image_path.unlink()

    db.delete(user)
    db.commit()

    audit_log = AuditLog(
        admin_user=current_user["username"],
        action="delete_user",
        resource_type="user",
        resource_id=user_id,
        details={"employee_id": employee_id, "name": name},
        ip_address=get_client_ip(request)
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"User deleted: {employee_id} - {name}")
    return {"message": "User deleted successfully"}


@router.post("/{user_id}/register-face", response_model=FaceRegistrationResult)
async def register_face(
    request: Request,
    user_id: str,
    face_image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin"))
):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return FaceRegistrationResult(
                success=False,
                message="User not found"
            )

        if not face_image.filename:
            return FaceRegistrationResult(
                success=False,
                message="No file provided"
            )

        file_ext = Path(face_image.filename).suffix.lower()
        if file_ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
            return FaceRegistrationResult(
                success=False,
                message=f"Invalid file type. Allowed: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS)}"
            )

        image_data = await face_image.read()

        if len(image_data) == 0:
            return FaceRegistrationResult(
                success=False,
                message="Empty file provided"
            )

        face_service = get_face_service()

        valid, message = face_service.validate_image(image_data)
        if not valid:
            return FaceRegistrationResult(success=False, message=message)

        detected, num_faces, detect_message = face_service.detect_faces(image_data)
        if not detected or num_faces != 1:
            return FaceRegistrationResult(success=False, message=detect_message)

        embedding, embed_message = face_service.extract_embedding(image_data)
        if embedding is None:
            return FaceRegistrationResult(success=False, message=embed_message)

        settings.FACES_DIR.mkdir(parents=True, exist_ok=True)
        image_filename = f"{user.id}{file_ext}"
        image_path = settings.FACES_DIR / image_filename

        if user.face_image_path and Path(user.face_image_path).exists():
            Path(user.face_image_path).unlink()

        with open(image_path, "wb") as f:
            f.write(image_data)

        user.face_embedding = embedding
        user.face_image_path = str(image_path)
        user.face_registered = True
        db.commit()

        audit_log = AuditLog(
            admin_user=current_user["username"],
            action="register_face",
            resource_type="user",
            resource_id=user.id,
            details={"employee_id": user.employee_id},
            ip_address=get_client_ip(request)
        )
        db.add(audit_log)
        db.commit()

        logger.info(f"Face registered for user: {user.employee_id}")
        return FaceRegistrationResult(
            success=True,
            message="Face registered successfully",
            user_id=user.id
        )
    except Exception as e:
        logger.error(f"Error registering face: {str(e)}")
        db.rollback()
        return FaceRegistrationResult(
            success=False,
            message=f"Error registering face: {str(e)}"
        )


@router.delete("/{user_id}/face")
async def remove_face(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin"))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.face_image_path:
        image_path = Path(user.face_image_path)
        if image_path.exists():
            image_path.unlink()

    user.face_embedding = None
    user.face_image_path = None
    user.face_registered = False
    db.commit()

    audit_log = AuditLog(
        admin_user=current_user["username"],
        action="remove_face",
        resource_type="user",
        resource_id=user.id,
        details={"employee_id": user.employee_id},
        ip_address=get_client_ip(request)
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Face removed for user: {user.employee_id}")
    return {"message": "Face data removed successfully"}
