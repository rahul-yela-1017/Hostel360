from __future__ import annotations

import json
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings
from .models import (
    AuditLog, Attendance, AttendanceStatus, Bed, BedStatus, HostelTiming, Notification, Room,
    RoomAllocation, RoomStatus, Student, User
)


def audit(db: Session, user_id: int | None, action: str, resource: str, resource_id=None, details=None):
    db.add(AuditLog(user_id=user_id, action=action, resource=resource,
                    resource_id=str(resource_id) if resource_id is not None else None, details=details))


def notify(db: Session, user_id: int, type_: str, title: str, message: str):
    db.add(Notification(user_id=user_id, type=type_, title=title, message=message))


def room_scope_for(user: User) -> int | None:
    if user.role.value == "WARDEN" and user.warden:
        return user.warden.hostel_id
    if user.role.value == "STUDENT" and user.student:
        return user.student.hostel_id
    if user.role.value == "COOK" and user.cook:
        return user.cook.hostel_id
    return None


def recompute_room_status(room: Room):
    occupied = sum(1 for bed in room.beds if bed.status == BedStatus.OCCUPIED)
    room.status = RoomStatus.EMPTY if occupied == 0 else RoomStatus.FULL if occupied == 4 else RoomStatus.PARTIALLY_OCCUPIED


def assign_student_to_bed(db: Session, student: Student, room: Room, bed: Bed, actor: User, reason: str):
    if room.hostel_id != student.hostel_id or bed.room_id != room.id:
        raise HTTPException(400, "The destination bed is outside the student's hostel")
    if bed.status != BedStatus.VACANT or bed.student is not None:
        raise HTTPException(409, "That bed is no longer available")

    old_bed = student.bed
    if old_bed:
        active = db.scalar(select(RoomAllocation).where(
            RoomAllocation.student_id == student.id,
            RoomAllocation.released_at.is_(None),
        ).with_for_update())
        if active:
            active.released_at = datetime.now(timezone.utc)
        old_bed.status = BedStatus.VACANT
        old_room = old_bed.room
    else:
        old_room = None

    # Lock destination in MySQL; unique students.bed_id is the final concurrency guard.
    db.execute(select(Bed).where(Bed.id == bed.id).with_for_update())
    bed.status = BedStatus.OCCUPIED
    student.bed = bed
    db.add(RoomAllocation(student_id=student.id, room_id=room.id, bed_id=bed.id,
                          reason=reason, changed_by=actor.id))
    recompute_room_status(room)
    if old_room and old_room.id != room.id:
        recompute_room_status(old_room)
    notify(db, student.user_id, "ROOM_CHANGED", "Room allocation updated",
           f"You are assigned to Room {room.room_number}, Bed {bed.bed_number}.")
    audit(db, actor.id, "STUDENT_BED_ASSIGNED", "student", student.id,
          {"room": room.room_number, "bed": bed.bed_number, "reason": reason})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "The requested bed was assigned by another operation") from exc


def record_attendance(db: Session, student: Student, kiosk_id: str, liveness_score: float,
                      captured_at: datetime | None = None) -> tuple[Attendance, bool]:
    ist = ZoneInfo("Asia/Kolkata")
    received = captured_at or datetime.now(timezone.utc)
    local_now = received.replace(tzinfo=ist) if received.tzinfo is None else received.astimezone(ist)
    attendance_date = local_now.date()
    existing = db.scalar(select(Attendance).where(
        Attendance.student_id == student.id,
        Attendance.attendance_date == attendance_date,
    ))
    if existing:
        return existing, False

    closing = time(22, 0)
    configured = db.scalar(select(HostelTiming.value).where(
        HostelTiming.hostel_id == student.hostel_id, HostelTiming.key == "gate_close"))
    if configured:
        for pattern in ("%I:%M %p", "%H:%M"):
            try:
                closing = datetime.strptime(configured.strip(), pattern).time()
                break
            except ValueError:
                continue
    status = AttendanceStatus.LATE if local_now.time().replace(tzinfo=None) > closing else AttendanceStatus.PRESENT
    row = Attendance(student_id=student.id, attendance_date=attendance_date,
                     attendance_time=local_now.time().replace(tzinfo=None), status=status,
                     verification_method="FACE", kiosk_id=kiosk_id, liveness_score=liveness_score)
    db.add(row)
    notify(db, student.user_id, "ATTENDANCE_RECORDED", "Attendance recorded",
           f"{status.value.title()} at {local_now.strftime('%I:%M %p')}.")
    audit(db, None, "KIOSK_ATTENDANCE_RECORDED", "attendance", None,
          {"student_id": student.id, "kiosk_id": kiosk_id, "status": status.value})
    try:
        db.commit()
        db.refresh(row)
        return row, True
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Attendance).where(
            Attendance.student_id == student.id,
            Attendance.attendance_date == attendance_date,
        ))
        return existing, False


def _fernet() -> Fernet:
    if settings.biometric_encryption_key:
        return Fernet(settings.biometric_encryption_key.encode())
    # Stable development key derived only for local demo; production must supply a managed key.
    import base64, hashlib
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key)


def encrypt_embedding(values: list[float]) -> bytes:
    return _fernet().encrypt(json.dumps(values, separators=(",", ":")).encode())


def decrypt_embedding(blob: bytes) -> list[float]:
    try:
        return json.loads(_fernet().decrypt(blob).decode())
    except (InvalidToken, ValueError) as exc:
        raise RuntimeError("Biometric data could not be decrypted") from exc


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return -1.0
    dot = sum(x*y for x, y in zip(a, b))
    na = sum(x*x for x in a) ** .5
    nb = sum(y*y for y in b) ** .5
    return dot / (na * nb) if na and nb else -1.0
