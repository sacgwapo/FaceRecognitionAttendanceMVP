"""
System settings routes.
"""

from typing import List
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SystemSettings, AuditLog
from app.schemas import SettingsUpdate, AuditLogResponse
from app.config import get_settings
from app.utils.security import get_current_user, get_client_ip, require_role
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/settings", tags=["Settings"])
logger = get_logger()
app_settings = get_settings()


@router.get("")
async def get_system_settings(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "hr"))
):
    settings_dict = {
        "face_match_threshold": app_settings.FACE_MATCH_THRESHOLD,
        "duplicate_attendance_timeout_minutes": app_settings.DUPLICATE_ATTENDANCE_TIMEOUT_MINUTES,
        "camera_index": app_settings.CAMERA_INDEX,
        "camera_width": app_settings.CAMERA_WIDTH,
        "camera_height": app_settings.CAMERA_HEIGHT,
        "face_detection_model": app_settings.FACE_DETECTION_MODEL,
        "max_upload_size_mb": app_settings.MAX_UPLOAD_SIZE_MB,
        "log_level": app_settings.LOG_LEVEL,
    }

    db_settings = db.query(SystemSettings).all()
    for setting in db_settings:
        settings_dict[setting.key] = setting.value

    return settings_dict


@router.put("")
async def update_system_settings(
    request: Request,
    settings_update: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin"))
):
    updated_fields = []

    for key, value in settings_update.model_dump(exclude_unset=True).items():
        if value is not None:
            existing = db.query(SystemSettings).filter(SystemSettings.key == key).first()
            if existing:
                existing.value = str(value)
            else:
                new_setting = SystemSettings(key=key, value=str(value))
                db.add(new_setting)
            updated_fields.append(key)

    db.commit()

    audit_log = AuditLog(
        admin_user=current_user["username"],
        action="update_settings",
        resource_type="settings",
        details={"updated_fields": updated_fields},
        ip_address=get_client_ip(request)
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Settings updated: {updated_fields}")
    return {"message": "Settings updated successfully", "updated": updated_fields}


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "hr"))
):
    logs = db.query(AuditLog).order_by(
        AuditLog.timestamp.desc()
    ).offset(offset).limit(limit).all()
    return logs


@router.get("/info")
async def get_system_info(
    current_user: str = Depends(get_current_user)
):
    return {
        "app_name": app_settings.APP_NAME,
        "version": app_settings.APP_VERSION,
        "data_dir": str(app_settings.DATA_DIR),
        "faces_dir": str(app_settings.FACES_DIR),
        "exports_dir": str(app_settings.EXPORTS_DIR),
        "logs_dir": str(app_settings.LOGS_DIR),
    }
