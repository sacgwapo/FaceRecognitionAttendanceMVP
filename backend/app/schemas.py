"""
Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr     


class UserBase(BaseModel):
    employee_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: str
    is_active: bool
    face_registered: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AttendanceRecordBase(BaseModel):
    date: str
    status: str = "present"
    notes: Optional[str] = None


class AttendanceRecordCreate(AttendanceRecordBase):
    user_id: Optional[str] = None
    employee_id: Optional[str] = None
    name: Optional[str] = None
    time_in: Optional[datetime] = None
    time_out: Optional[datetime] = None
    confidence_score: Optional[float] = None
    is_recognized: bool = True


class AttendanceRecordUpdate(BaseModel):
    time_out: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class AttendanceRecordResponse(BaseModel):
    id: str
    user_id: Optional[str]
    employee_id: Optional[str]
    name: Optional[str]
    date: str
    time_in: Optional[datetime]
    time_out: Optional[datetime]
    status: str
    confidence_score: Optional[float]
    is_recognized: bool
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class RecognitionResult(BaseModel):
    recognized: bool
    user_id: Optional[str] = None
    employee_id: Optional[str] = None
    name: Optional[str] = None
    confidence: float
    message: str
    attendance_id: Optional[str] = None


class FaceRegistrationResult(BaseModel):
    success: bool
    message: str
    user_id: Optional[str] = None


class LoginRequest(BaseModel):
    username: str = Field(..., max_length=50)
    password: str = Field(..., max_length=72)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class SettingsUpdate(BaseModel):
    face_match_threshold: Optional[float] = Field(None, ge=0.1, le=1.0)
    duplicate_attendance_timeout_minutes: Optional[int] = Field(None, ge=1, le=1440)
    camera_index: Optional[int] = Field(None, ge=0)


class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    registered_faces: int
    today_attendance: int
    today_time_ins: int
    today_time_outs: int
    today_unrecognized: int


class ExportRequest(BaseModel):
    start_date: str
    end_date: str
    format: str = "xlsx"
    include_unrecognized: bool = True


class AuditLogResponse(BaseModel):
    id: str
    timestamp: datetime
    admin_user: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[dict]
    ip_address: Optional[str]

    class Config:
        from_attributes = True


class AdminUserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=72)
    full_name: Optional[str] = Field(None, max_length=100)
    role: str = Field(..., pattern="^(admin|hr|attendance)$")


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=6, max_length=72)
    role: Optional[str] = Field(None, pattern="^(admin|hr|attendance)$")
    is_active: Optional[bool] = None


class AdminUserResponse(BaseModel):
    id: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class LoginResponse(Token):
    role: str
    username: str
    full_name: Optional[str]
