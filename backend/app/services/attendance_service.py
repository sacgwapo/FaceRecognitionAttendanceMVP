"""
Attendance management service.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models import AttendanceRecord, User
from app.schemas import AttendanceRecordCreate
from app.config import get_settings
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger()


class AttendanceService:
    def __init__(self, db: Session):
        self.db = db

    def check_duplicate_attendance(
        self,
        user_id: Optional[str],
        employee_id: Optional[str],
        check_type: str = "time_in"
    ) -> Tuple[bool, Optional[AttendanceRecord]]:
        today = datetime.now().strftime("%Y-%m-%d")
        timeout_minutes = settings.DUPLICATE_ATTENDANCE_TIMEOUT_MINUTES
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)

        query = self.db.query(AttendanceRecord).filter(
            AttendanceRecord.date == today
        )

        if user_id:
            query = query.filter(AttendanceRecord.user_id == user_id)
        elif employee_id:
            query = query.filter(AttendanceRecord.employee_id == employee_id)
        else:
            return False, None

        if check_type == "time_in":
            query = query.filter(AttendanceRecord.time_in >= cutoff_time)
        else:
            query = query.filter(AttendanceRecord.time_out >= cutoff_time)

        existing = query.order_by(AttendanceRecord.created_at.desc()).first()

        if existing:
            return True, existing
        return False, None

    def get_todays_record(
        self,
        user_id: Optional[str] = None,
        employee_id: Optional[str] = None
    ) -> Optional[AttendanceRecord]:
        today = datetime.now().strftime("%Y-%m-%d")
        query = self.db.query(AttendanceRecord).filter(
            AttendanceRecord.date == today
        )

        if user_id:
            query = query.filter(AttendanceRecord.user_id == user_id)
        elif employee_id:
            query = query.filter(AttendanceRecord.employee_id == employee_id)
        else:
            return None

        return query.filter(AttendanceRecord.time_out.is_(None)).order_by(
            AttendanceRecord.time_in.desc()
        ).first()

    def record_time_in(
        self,
        user_id: Optional[str],
        employee_id: Optional[str],
        name: Optional[str],
        confidence_score: float,
        is_recognized: bool
    ) -> Tuple[AttendanceRecord, str]:
        is_duplicate, existing = self.check_duplicate_attendance(
            user_id, employee_id, "time_in"
        )

        if is_duplicate and existing:
            timeout = settings.DUPLICATE_ATTENDANCE_TIMEOUT_MINUTES
            return existing, f"Duplicate entry. Already checked in within {timeout} minutes."

        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now()

        record = AttendanceRecord(
            user_id=user_id,
            employee_id=employee_id,
            name=name,
            date=today,
            time_in=now,
            time_out=None,
            status="present",
            confidence_score=confidence_score,
            is_recognized=is_recognized,
            notes="Auto-recorded via face recognition" if is_recognized else "Unrecognized face"
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        logger.info(f"Time-in recorded for {name or employee_id or 'Unknown'}")
        return record, "Time-in recorded successfully"

    def record_time_out(
        self,
        user_id: Optional[str] = None,
        employee_id: Optional[str] = None
    ) -> Tuple[Optional[AttendanceRecord], str]:
        existing = self.get_todays_record(user_id, employee_id)

        if not existing:
            return None, "No open time-in record found for today"

        is_duplicate, _ = self.check_duplicate_attendance(
            user_id, employee_id, "time_out"
        )

        if is_duplicate:
            timeout = settings.DUPLICATE_ATTENDANCE_TIMEOUT_MINUTES
            return existing, f"Duplicate entry. Already checked out within {timeout} minutes."

        existing.time_out = datetime.now()
        existing.status = "completed"
        self.db.commit()
        self.db.refresh(existing)

        logger.info(f"Time-out recorded for {existing.name or existing.employee_id}")
        return existing, "Time-out recorded successfully"

    def get_attendance_records(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        employee_id: Optional[str] = None,
        name: Optional[str] = None,
        status: Optional[str] = None,
        include_unrecognized: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[AttendanceRecord]:
        query = self.db.query(AttendanceRecord)

        if start_date:
            query = query.filter(AttendanceRecord.date >= start_date)
        if end_date:
            query = query.filter(AttendanceRecord.date <= end_date)
        if employee_id:
            query = query.filter(AttendanceRecord.employee_id.ilike(f"%{employee_id}%"))
        if name:
            query = query.filter(AttendanceRecord.name.ilike(f"%{name}%"))
        if status:
            query = query.filter(AttendanceRecord.status == status)
        if not include_unrecognized:
            query = query.filter(AttendanceRecord.is_recognized == True)

        return query.order_by(
            AttendanceRecord.date.desc(),
            AttendanceRecord.time_in.desc()
        ).offset(offset).limit(limit).all()

    def get_today_stats(self) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")

        total = self.db.query(func.count(AttendanceRecord.id)).filter(
            AttendanceRecord.date == today
        ).scalar()

        time_ins = self.db.query(func.count(AttendanceRecord.id)).filter(
            and_(
                AttendanceRecord.date == today,
                AttendanceRecord.time_in.isnot(None)
            )
        ).scalar()

        time_outs = self.db.query(func.count(AttendanceRecord.id)).filter(
            and_(
                AttendanceRecord.date == today,
                AttendanceRecord.time_out.isnot(None)
            )
        ).scalar()

        unrecognized = self.db.query(func.count(AttendanceRecord.id)).filter(
            and_(
                AttendanceRecord.date == today,
                AttendanceRecord.is_recognized == False
            )
        ).scalar()

        return {
            "total": total or 0,
            "time_ins": time_ins or 0,
            "time_outs": time_outs or 0,
            "unrecognized": unrecognized or 0
        }
