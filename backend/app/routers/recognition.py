"""
Face recognition routes for attendance marking.

This endpoint is used by the recognition page to identify users
and automatically record their attendance.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import RecognitionResult
from app.services.face_recognition_service import get_face_service
from app.services.attendance_service import AttendanceService
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/recognition", tags=["Recognition"])
logger = get_logger()


@router.post("/identify", response_model=RecognitionResult)
async def identify_face(
    face_image: UploadFile = File(...),
    action: str = Form("time_in"),
    db: Session = Depends(get_db)
):
    import os
    from datetime import datetime
    from pathlib import Path
    from app.config import get_settings

    settings = get_settings()
    image_data = await face_image.read()

    face_service = get_face_service()

    valid, message = face_service.validate_image(image_data)
    if not valid:
        return RecognitionResult(
            recognized=False,
            confidence=0.0,
            message=message
        )

    snapshot_path = None
    try:
        snapshots_dir = settings.DATA_DIR / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        snapshot_filename = f"snapshot_{timestamp}.jpg"
        snapshot_path = snapshots_dir / snapshot_filename

        with open(snapshot_path, 'wb') as f:
            f.write(image_data)

        logger.info(f"Snapshot saved: {snapshot_path}")
    except Exception as e:
        logger.error(f"Failed to save snapshot: {e}")
        snapshot_path = None

    registered_users = db.query(User).filter(
        User.face_registered == True,
        User.is_active == True,
        User.face_embedding.isnot(None)
    ).all()

    if not registered_users:
        return RecognitionResult(
            recognized=False,
            confidence=0.0,
            message="No registered faces in the system"
        )

    embeddings = [
        (user.id, user.employee_id, user.name, user.face_embedding)
        for user in registered_users
    ]

    user_id, employee_id, name, confidence, compare_message = face_service.compare_faces(
        image_data, embeddings
    )

    attendance_service = AttendanceService(db)

    if user_id:
        if action == "time_in":
            record, att_message = attendance_service.record_time_in(
                user_id=user_id,
                employee_id=employee_id,
                name=name,
                confidence_score=confidence,
                is_recognized=True
            )
            return RecognitionResult(
                recognized=True,
                user_id=user_id,
                employee_id=employee_id,
                name=name,
                confidence=confidence,
                message=att_message,
                attendance_id=record.id
            )
        else:
            record, att_message = attendance_service.record_time_out(
                user_id=user_id,
                employee_id=employee_id
            )
            if record:
                return RecognitionResult(
                    recognized=True,
                    user_id=user_id,
                    employee_id=employee_id,
                    name=name,
                    confidence=confidence,
                    message=att_message,
                    attendance_id=record.id
                )
            else:
                return RecognitionResult(
                    recognized=True,
                    user_id=user_id,
                    employee_id=employee_id,
                    name=name,
                    confidence=confidence,
                    message=att_message
                )
    else:
        if action == "time_in":
            record, att_message = attendance_service.record_time_in(
                user_id=None,
                employee_id=None,
                name="Unrecognized",
                confidence_score=confidence,
                is_recognized=False
            )
            return RecognitionResult(
                recognized=False,
                confidence=confidence,
                message=f"Face not recognized (confidence: {confidence:.1%}). Logged as unrecognized.",
                attendance_id=record.id
            )
        else:
            return RecognitionResult(
                recognized=False,
                confidence=confidence,
                message="Face not recognized. Cannot record time-out for unknown person."
            )


@router.post("/detect")
async def detect_face(
    face_image: UploadFile = File(...)
):
    image_data = await face_image.read()
    face_service = get_face_service()

    valid, message = face_service.validate_image(image_data)
    if not valid:
        return {"detected": False, "count": 0, "message": message}

    detected, count, message = face_service.detect_faces(image_data)

    return {
        "detected": detected,
        "count": count,
        "message": message
    }


@router.get("/threshold")
async def get_threshold():
    face_service = get_face_service()
    return {"threshold": face_service.get_current_threshold()}
