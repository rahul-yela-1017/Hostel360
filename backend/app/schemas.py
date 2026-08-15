from datetime import date, datetime, time
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from .models import Role, AccountStatus, AttendanceStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class InitialAdminCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=8, max_length=20)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str):
        if not (any(c.isupper() for c in value) and any(c.islower() for c in value)
                and any(c.isdigit() for c in value) and any(not c.isalnum() for c in value)):
            raise ValueError("Password must include upper-case, lower-case, number and symbol")
        return value


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong_new_password(cls, value: str):
        if not (any(c.isupper() for c in value) and any(c.islower() for c in value)
                and any(c.isdigit() for c in value) and any(not c.isalnum() for c in value)):
            raise ValueError("Password must include upper-case, lower-case, number and symbol")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class StaffCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=8, max_length=20)
    employee_id: str | None = None
    designation: str | None = None
    assigned_area: str | None = None
    hostel_id: int = 1
    temporary_password: str = Field(min_length=10, max_length=128)


class StaffUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = None
    designation: str | None = None
    assigned_area: str | None = None
    status: AccountStatus | None = None


class StudentCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    roll_no: str = Field(min_length=3, max_length=50)
    phone: str = Field(min_length=8, max_length=20)
    email: EmailStr
    course: str
    branch: str
    year: int = Field(ge=1, le=8)
    parent_name: str
    parent_phone: str
    emergency_contact: str
    student_id: str
    hostel_id: int = 1
    room_number: int | None = Field(default=None, ge=0, le=430)
    bed_number: int | None = Field(default=None, ge=1, le=4)
    temporary_password: str | None = Field(default=None, min_length=10, max_length=128)

    @field_validator("bed_number")
    @classmethod
    def bed_requires_room(cls, value, info):
        if value is not None and info.data.get("room_number") is None:
            raise ValueError("room_number is required when bed_number is supplied")
        return value


class StudentUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    course: str | None = None
    branch: str | None = None
    year: int | None = Field(default=None, ge=1, le=8)
    parent_name: str | None = None
    parent_phone: str | None = None
    emergency_contact: str | None = None
    status: AccountStatus | None = None


class BedAssignment(BaseModel):
    room_number: int = Field(ge=0, le=430)
    bed_number: int = Field(ge=1, le=4)
    reason: str = Field(default="Room assignment", max_length=255)


class MenuUpsert(BaseModel):
    menu_date: date
    breakfast: str = Field(min_length=2)
    breakfast_time: str = "08:00 AM – 09:30 AM"
    lunch: str = Field(min_length=2)
    lunch_time: str = "12:30 PM – 02:00 PM"
    snacks: str = Field(min_length=2)
    snacks_time: str = "04:30 PM – 05:30 PM"
    dinner: str = Field(min_length=2)
    dinner_time: str = "07:30 PM – 09:30 PM"
    description: str | None = None
    publish: bool = True
    hostel_id: int = 1
    reason: str | None = None


class NoticeCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    message: str = Field(min_length=3)
    priority: Literal["NORMAL", "IMPORTANT", "URGENT"] = "NORMAL"
    hostel_id: int = 1
    expires_at: datetime | None = None


class TimingUpdate(BaseModel):
    value: str = Field(min_length=2, max_length=80)


class FaceEnrollRequest(BaseModel):
    student_id: int
    embedding: list[float] = Field(min_length=64, max_length=1024)
    model_version: str = "provider-v1"
    liveness_score: float = Field(ge=0, le=1)


class KioskAttendanceRequest(BaseModel):
    device_id: str = Field(min_length=3, max_length=80)
    embedding: list[float] = Field(min_length=64, max_length=1024)
    liveness_score: float = Field(ge=0, le=1)
    captured_at: datetime | None = None


class ManualAttendanceMark(BaseModel):
    student_id: int = Field(gt=0)
    attendance_date: date
    attendance_time: time
    status: AttendanceStatus


class LeaveCreate(BaseModel):
    from_date: date
    to_date: date
    reason: str = Field(min_length=3)


class ReportFilter(BaseModel):
    room_from: int = Field(default=0, ge=0, le=430)
    room_to: int = Field(default=430, ge=0, le=430)
    status: Literal["All", "Occupied", "Partially Occupied", "Empty"] = "All"
    format: Literal["csv", "xlsx", "zip"] = "zip"
