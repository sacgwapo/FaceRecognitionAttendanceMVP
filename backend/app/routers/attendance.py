"""
Attendance management routes.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AttendanceRecord
from app.schemas import AttendanceRecordResponse, AttendanceRecordUpdate
from app.services.attendance_service import AttendanceService
from app.utils.security import get_current_user
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])
logger = get_logger()


@router.get("", response_model=List[AttendanceRecordResponse])
async def list_attendance(
    start_date: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    employee_id: Optional[str] = Query(None, description="Filter by employee ID"),
    name: Optional[str] = Query(None, description="Filter by name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    include_unrecognized: bool = Query(True, description="Include unrecognized entries"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    service = AttendanceService(db)
    records = service.get_attendance_records(
        start_date=start_date,
        end_date=end_date,
        employee_id=employee_id,
        name=name,
        status=status,
        include_unrecognized=include_unrecognized,
        limit=limit,
        offset=offset
    )
    return records


@router.get("/today", response_model=List[AttendanceRecordResponse])
async def get_today_attendance(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    today = datetime.now().strftime("%Y-%m-%d")
    service = AttendanceService(db)
    records = service.get_attendance_records(
        start_date=today,
        end_date=today,
        limit=500
    )
    return records


@router.get("/stats")
async def get_attendance_stats(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    service = AttendanceService(db)
    return service.get_today_stats()


@router.get("/{record_id}", response_model=AttendanceRecordResponse)
async def get_attendance_record(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    record = db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.put("/{record_id}", response_model=AttendanceRecordResponse)
async def update_attendance_record(
    record_id: str,
    update_data: AttendanceRecordUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    record = db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)

    logger.info(f"Attendance record updated: {record_id}")
    return record


@router.delete("/{record_id}")
async def delete_attendance_record(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    record = db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    db.delete(record)
    db.commit()

    logger.info(f"Attendance record deleted: {record_id}")
    return {"message": "Record deleted successfully"}
