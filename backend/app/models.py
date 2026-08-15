from __future__ import annotations

from datetime import date, datetime, time, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Enum as SQLEnum, Float, ForeignKey,
    Integer, LargeBinary, String, Text, Time, UniqueConstraint, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, Enum):
    ADMIN = "ADMIN"
    WARDEN = "WARDEN"
    COOK = "COOK"
    STUDENT = "STUDENT"


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class RoomStatus(str, Enum):
    EMPTY = "EMPTY"
    PARTIALLY_OCCUPIED = "PARTIALLY_OCCUPIED"
    FULL = "FULL"


class BedStatus(str, Enum):
    VACANT = "VACANT"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    LATE = "LATE"
    ABSENT = "ABSENT"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    firebase_uid: Mapped[Optional[str]] = mapped_column(String(128), unique=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[str] = mapped_column(String(190), unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SQLEnum(Role), index=True)
    status: Mapped[AccountStatus] = mapped_column(SQLEnum(AccountStatus), default=AccountStatus.ACTIVE, index=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    student: Mapped[Optional[Student]] = relationship(back_populates="user", uselist=False)
    warden: Mapped[Optional[Warden]] = relationship(back_populates="user", uselist=False)
    cook: Mapped[Optional[Cook]] = relationship(back_populates="user", uselist=False)


class Hostel(Base):
    __tablename__ = "hostels"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    address: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    rooms: Mapped[list[Room]] = relationship(back_populates="hostel")


class Warden(Base):
    __tablename__ = "wardens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    employee_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    hostel_id: Mapped[int] = mapped_column(ForeignKey("hostels.id"), index=True)
    designation: Mapped[str] = mapped_column(String(100), default="Warden")
    availability: Mapped[str] = mapped_column(String(80), default="Day Shift")
    user: Mapped[User] = relationship(back_populates="warden")
    hostel: Mapped[Hostel] = relationship()


class Cook(Base):
    __tablename__ = "cooks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    employee_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    hostel_id: Mapped[int] = mapped_column(ForeignKey("hostels.id"), index=True)
    assigned_mess: Mapped[str] = mapped_column(String(100), default="Main Mess")
    user: Mapped[User] = relationship(back_populates="cook")
    hostel: Mapped[Hostel] = relationship()


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("hostel_id", "room_number", name="uq_hostel_room"),
        CheckConstraint("room_number >= 0 AND room_number <= 430", name="ck_room_number"),
        CheckConstraint("capacity = 4", name="ck_room_capacity"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    hostel_id: Mapped[int] = mapped_column(ForeignKey("hostels.id"), index=True)
    room_number: Mapped[int] = mapped_column(Integer, index=True)
    capacity: Mapped[int] = mapped_column(Integer, default=4)
    status: Mapped[RoomStatus] = mapped_column(SQLEnum(RoomStatus), default=RoomStatus.EMPTY, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    hostel: Mapped[Hostel] = relationship(back_populates="rooms")
    beds: Mapped[list[Bed]] = relationship(back_populates="room", cascade="all, delete-orphan", order_by="Bed.bed_number")


class Bed(Base):
    __tablename__ = "beds"
    __table_args__ = (
        UniqueConstraint("room_id", "bed_number", name="uq_room_bed"),
        CheckConstraint("bed_number >= 1 AND bed_number <= 4", name="ck_bed_number"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    bed_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[BedStatus] = mapped_column(SQLEnum(BedStatus), default=BedStatus.VACANT, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    room: Mapped[Room] = relationship(back_populates="beds")
    student: Mapped[Optional[Student]] = relationship(back_populates="bed", uselist=False)


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    hostel_id: Mapped[int] = mapped_column(ForeignKey("hostels.id"), index=True)
    student_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    roll_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    course: Mapped[str] = mapped_column(String(100))
    branch: Mapped[str] = mapped_column(String(100))
    year: Mapped[int] = mapped_column(Integer)
    parent_name: Mapped[str] = mapped_column(String(120))
    parent_phone: Mapped[str] = mapped_column(String(20))
    emergency_contact: Mapped[str] = mapped_column(String(20))
    bed_id: Mapped[Optional[int]] = mapped_column(ForeignKey("beds.id"), unique=True, index=True)
    face_enrolled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="student")
    hostel: Mapped[Hostel] = relationship()
    bed: Mapped[Optional[Bed]] = relationship(back_populates="student")
    attendance: Mapped[list[Attendance]] = relationship(back_populates="student", cascade="all, delete-orphan")


class RoomAllocation(Base):
    __tablename__ = "room_allocations"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), index=True)
    bed_id: Mapped[int] = mapped_column(ForeignKey("beds.id"), index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(String(255), default="Initial allocation")
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("student_id", "attendance_date", name="uq_student_attendance_day"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    attendance_date: Mapped[date] = mapped_column(Date, index=True)
    attendance_time: Mapped[time] = mapped_column(Time)
    status: Mapped[AttendanceStatus] = mapped_column(SQLEnum(AttendanceStatus), index=True)
    verification_method: Mapped[str] = mapped_column(String(30), default="FACE")
    kiosk_id: Mapped[Optional[str]] = mapped_column(String(80))
    liveness_score: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    student: Mapped[Student] = relationship(back_populates="attendance")


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), unique=True)
    encrypted_embedding: Mapped[bytes] = mapped_column(LargeBinary)
    model_version: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Menu(Base):
    __tablename__ = "menus"
    __table_args__ = (UniqueConstraint("hostel_id", "menu_date", name="uq_hostel_menu_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    hostel_id: Mapped[int] = mapped_column(ForeignKey("hostels.id"), index=True)
    menu_date: Mapped[date] = mapped_column(Date, index=True)
    breakfast: Mapped[str] = mapped_column(Text)
    breakfast_time: Mapped[str] = mapped_column(String(40), default="08:00 AM – 09:30 AM")
    lunch: Mapped[str] = mapped_column(Text)
    lunch_time: Mapped[str] = mapped_column(String(40), default="12:30 PM – 02:00 PM")
    snacks: Mapped[str] = mapped_column(Text)
    snacks_time: Mapped[str] = mapped_column(String(40), default="04:30 PM – 05:30 PM")
    dinner: Mapped[str] = mapped_column(Text)
    dinner_time: Mapped[str] = mapped_column(String(40), default="07:30 PM – 09:30 PM")
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    published_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MenuHistory(Base):
    __tablename__ = "menu_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    menu_id: Mapped[int] = mapped_column(ForeignKey("menus.id", ondelete="CASCADE"), index=True)
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    meal_type: Mapped[str] = mapped_column(String(30))
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    reason: Mapped[Optional[str]] = mapped_column(String(255))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class HostelTiming(Base):
    __tablename__ = "hostel_timings"
    __table_args__ = (UniqueConstraint("hostel_id", "key", name="uq_hostel_timing"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    hostel_id: Mapped[int] = mapped_column(ForeignKey("hostels.id"), index=True)
    key: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(120))
    value: Mapped[str] = mapped_column(String(80))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    updated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Notice(Base):
    __tablename__ = "notices"
    id: Mapped[int] = mapped_column(primary_key=True)
    hostel_id: Mapped[int] = mapped_column(ForeignKey("hostels.id"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL")
    published_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    from_date: Mapped[date] = mapped_column(Date)
    to_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KioskDevice(Base):
    __tablename__ = "kiosk_devices"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    hostel_id: Mapped[int] = mapped_column(ForeignKey("hostels.id"))
    name: Mapped[str] = mapped_column(String(120))
    api_key_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    resource: Mapped[str] = mapped_column(String(80), index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(80))
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
