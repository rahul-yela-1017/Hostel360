from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload
from ..config import settings
from ..database import get_db
from ..deps import get_current_user, require_roles
from ..models import (
    AccountStatus, Attendance, AttendanceStatus, Bed, BedStatus, HostelTiming,
    Notice, Notification, Role, Room, RoomStatus, Student, User, Warden
)
from ..schemas import BedAssignment, ManualAttendanceMark, NoticeCreate, StudentCreate, StudentUpdate, TimingUpdate
from ..security import hash_password
from ..services import assign_student_to_bed, audit, notify, room_scope_for

router = APIRouter(tags=["Hostel Operations"])
IST = ZoneInfo("Asia/Kolkata")


def today_ist() -> date:
    return datetime.now(IST).date()


def student_row(student: Student, private: bool = False) -> dict:
    bed = student.bed
    data = {
        "id": student.id, "name": student.user.name, "student_id": student.student_id,
        "roll_no": student.roll_no, "course": student.course, "branch": student.branch,
        "year": student.year, "status": student.user.status.value,
        "room": bed.room.room_number if bed else None, "bed": bed.bed_number if bed else None,
        "face_enrolled": student.face_enrolled,
    }
    if private:
        data.update({"phone": student.user.phone, "email": student.user.email,
                     "parent_name": student.parent_name, "parent_phone": student.parent_phone,
                     "emergency_contact": student.emergency_contact})
    return data


def room_row(room: Room, include_students: bool = False) -> dict:
    beds = []
    for bed in room.beds:
        entry = {"id": bed.id, "bed_number": bed.bed_number, "status": bed.status.value}
        if include_students:
            entry["student"] = ({"id": bed.student.id, "name": bed.student.user.name,
                                  "roll_no": bed.student.roll_no} if bed.student else None)
        beds.append(entry)
    occupied = sum(1 for bed in room.beds if bed.status == BedStatus.OCCUPIED)
    return {"id": room.id, "room_number": room.room_number, "capacity": 4, "occupied": occupied,
            "available": sum(1 for bed in room.beds if bed.status == BedStatus.VACANT),
            "status": room.status.value, "beds": beds if include_students else None}


def enforce_hostel_scope(user: User, hostel_id: int):
    scope = room_scope_for(user)
    if scope is not None and scope != hostel_id:
        raise HTTPException(403, "This record is outside your authorized hostel scope")


@router.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    hostel_id = room_scope_for(user) or 1
    day = today_ist()
    total_students = db.scalar(select(func.count(Student.id)).where(Student.hostel_id == hostel_id)) or 0
    total_rooms = db.scalar(select(func.count(Room.id)).where(Room.hostel_id == hostel_id)) or 0
    occupied_beds = db.scalar(select(func.count(Bed.id)).join(Room).where(Room.hostel_id == hostel_id, Bed.status == BedStatus.OCCUPIED)) or 0
    counts = dict(db.execute(select(Attendance.status, func.count(Attendance.id)).join(Student).where(
        Student.hostel_id == hostel_id, Attendance.attendance_date == day).group_by(Attendance.status)).all())
    present = counts.get(AttendanceStatus.PRESENT, 0) + counts.get(AttendanceStatus.LATE, 0)
    absent = counts.get(AttendanceStatus.ABSENT, 0)
    late = counts.get(AttendanceStatus.LATE, 0)
    not_recorded = max(total_students - present - absent, 0)

    trend = []
    for offset in range(6, -1, -1):
        target = day - timedelta(days=offset)
        attended = db.scalar(select(func.count(Attendance.id)).join(Student).where(
            Student.hostel_id == hostel_id, Attendance.attendance_date == target,
            Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE]))) or 0
        trend.append({"date": target.strftime("%a"), "attendance": round(attended * 100 / total_students, 1) if total_students else 0})

    base = {
        "total_students": total_students, "total_rooms": total_rooms, "total_beds": total_rooms * 4,
        "occupied_beds": occupied_beds, "vacant_beds": total_rooms * 4 - occupied_beds,
        "present": present, "absent": absent, "not_recorded": not_recorded, "late": late,
        "attendance_percentage": round(present * 100 / total_students, 2) if total_students else 0,
        "occupancy_percentage": round(occupied_beds * 100 / (total_rooms * 4), 2) if total_rooms else 0,
        "trend": trend,
    }
    if user.role == Role.ADMIN:
        base.update({
            "total_wardens": db.scalar(select(func.count(User.id)).where(User.role == Role.WARDEN)) or 0,
            "total_cooks": db.scalar(select(func.count(User.id)).where(User.role == Role.COOK)) or 0,
            "active_users": db.scalar(select(func.count(User.id)).where(User.status == AccountStatus.ACTIVE)) or 0,
        })
    return base


@router.get("/warden/students")
def list_students(
    q: str | None = None, room: int | None = Query(None, ge=0, le=430),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), user: User = Depends(require_roles(Role.ADMIN, Role.WARDEN)),
):
    hostel_id = room_scope_for(user) or 1
    query = select(Student).join(Student.user).outerjoin(Student.bed).outerjoin(Bed.room).where(Student.hostel_id == hostel_id)
    if q:
        term = f"%{q.strip()}%"
        query = query.where(or_(User.name.ilike(term), Student.roll_no.ilike(term), Student.student_id.ilike(term)))
    if room is not None:
        query = query.where(Room.room_number == room)
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = db.scalars(query.options(joinedload(Student.user), joinedload(Student.bed).joinedload(Bed.room))
                      .order_by(User.name).offset((page-1)*page_size).limit(page_size)).unique().all()
    return {"items": [student_row(s) for s in rows], "total": total, "page": page, "page_size": page_size}


@router.post("/warden/students", status_code=201)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles(Role.ADMIN, Role.WARDEN))):
    enforce_hostel_scope(actor, payload.hostel_id)
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(409, "Email already exists")
    if db.scalar(select(Student).where(or_(Student.roll_no == payload.roll_no, Student.student_id == payload.student_id))):
        raise HTTPException(409, "Roll number or Student ID already exists")
    initial_password = payload.temporary_password or settings.student_initial_password
    user = User(name=payload.full_name, email=payload.email.lower(), phone=payload.phone,
                password_hash=hash_password(initial_password), role=Role.STUDENT,
                status=AccountStatus.ACTIVE, must_change_password=True)
    db.add(user); db.flush()
    student = Student(user_id=user.id, hostel_id=payload.hostel_id, student_id=payload.student_id,
                      roll_no=payload.roll_no, course=payload.course, branch=payload.branch, year=payload.year,
                      parent_name=payload.parent_name, parent_phone=payload.parent_phone,
                      emergency_contact=payload.emergency_contact)
    db.add(student); db.flush()
    audit(db, actor.id, "STUDENT_CREATED", "student", student.id)
    if payload.room_number is not None and payload.bed_number is not None:
        room = db.scalar(select(Room).where(Room.hostel_id == payload.hostel_id, Room.room_number == payload.room_number)
                         .options(selectinload(Room.beds)))
        bed = next((b for b in room.beds if b.bed_number == payload.bed_number), None) if room else None
        if not room or not bed:
            db.rollback()
            raise HTTPException(404, "Room or bed not found")
        # The account, student profile and bed allocation commit as one transaction.
        assign_student_to_bed(db, student, room, bed, actor, "Initial allocation")
    else:
        db.commit()
    db.refresh(student)
    return student_row(student, private=True)


@router.get("/warden/students/{student_id}")
def get_student(student_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.ADMIN, Role.WARDEN))):
    student = db.scalar(select(Student).where(Student.id == student_id).options(
        joinedload(Student.user), joinedload(Student.bed).joinedload(Bed.room)))
    if not student: raise HTTPException(404, "Student not found")
    enforce_hostel_scope(user, student.hostel_id)
    data = student_row(student, private=True)
    history = db.scalars(select(Attendance).where(Attendance.student_id == student.id)
                         .order_by(Attendance.attendance_date.desc()).limit(30)).all()
    data["attendance"] = [{"date": r.attendance_date, "time": r.attendance_time.strftime("%H:%M"), "status": r.status.value} for r in history]
    return data


@router.patch("/warden/students/{student_id}")
def update_student(student_id: int, payload: StudentUpdate, db: Session = Depends(get_db), actor: User = Depends(require_roles(Role.ADMIN, Role.WARDEN))):
    student = db.get(Student, student_id)
    if not student: raise HTTPException(404, "Student not found")
    enforce_hostel_scope(actor, student.hostel_id)
    values = payload.model_dump(exclude_unset=True)
    for key in ("course", "branch", "year", "parent_name", "parent_phone", "emergency_contact"):
        if key in values: setattr(student, key, values[key])
    for key, target in (("full_name", "name"), ("phone", "phone"), ("email", "email"), ("status", "status")):
        if key in values: setattr(student.user, target, values[key])
    audit(db, actor.id, "STUDENT_UPDATED", "student", student.id, values)
    db.commit()
    return student_row(student, private=True)


@router.post("/warden/students/{student_id}/reset-password")
def reset_student_password(student_id: int, db: Session = Depends(get_db), actor: User = Depends(require_roles(Role.ADMIN, Role.WARDEN))):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    enforce_hostel_scope(actor, student.hostel_id)
    student.user.password_hash = hash_password(settings.student_initial_password)
    student.user.must_change_password = True
    audit(db, actor.id, "STUDENT_PASSWORD_RESET", "student", student.id)
    db.commit()
    return {"message": "Student password reset to the hostel initial password"}


@router.post("/warden/students/{student_id}/assign-bed")
@router.post("/warden/students/{student_id}/transfer")
def assign_bed(student_id: int, payload: BedAssignment, db: Session = Depends(get_db), actor: User = Depends(require_roles(Role.ADMIN, Role.WARDEN))):
    student = db.scalar(select(Student).where(Student.id == student_id).options(joinedload(Student.bed).joinedload(Bed.room)))
    if not student: raise HTTPException(404, "Student not found")
    enforce_hostel_scope(actor, student.hostel_id)
    room = db.scalar(select(Room).where(Room.hostel_id == student.hostel_id, Room.room_number == payload.room_number)
                     .options(selectinload(Room.beds)))
    if not room: raise HTTPException(404, "Room not found")
    bed = next((b for b in room.beds if b.bed_number == payload.bed_number), None)
    if not bed: raise HTTPException(404, "Bed not found")
    assign_student_to_bed(db, student, room, bed, actor, payload.reason)
    return {"message": "Room transfer completed", "student": student_row(student)}


@router.get("/warden/rooms")
def list_rooms(
    q: int | None = Query(None, ge=0, le=430), status: RoomStatus | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db), user: User = Depends(require_roles(Role.ADMIN, Role.WARDEN)),
):
    hostel_id = room_scope_for(user) or 1
    query = select(Room).where(Room.hostel_id == hostel_id)
    if q is not None: query = query.where(Room.room_number == q)
    if status: query = query.where(Room.status == status)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rooms = db.scalars(query.options(selectinload(Room.beds)).order_by(Room.room_number)
                       .offset((page-1)*page_size).limit(page_size)).all()
    return {"items": [room_row(r) for r in rooms], "total": total, "page": page, "page_size": page_size}


@router.get("/warden/rooms/{room_number}")
def get_room(room_number: int, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.ADMIN, Role.WARDEN))):
    hostel_id = room_scope_for(user) or 1
    room = db.scalar(select(Room).where(Room.hostel_id == hostel_id, Room.room_number == room_number).options(
        selectinload(Room.beds).selectinload(Bed.student).joinedload(Student.user)))
    if not room: raise HTTPException(404, "Room not found")
    return room_row(room, include_students=True)


@router.post("/attendance/mark")
def mark_attendance(payload: ManualAttendanceMark, db: Session = Depends(get_db), actor: User = Depends(require_roles(Role.ADMIN, Role.WARDEN))):
    student = db.scalar(select(Student).where(Student.id == payload.student_id).options(joinedload(Student.user)))
    if not student:
        raise HTTPException(404, "Student not found")
    enforce_hostel_scope(actor, student.hostel_id)
    row = db.scalar(select(Attendance).where(
        Attendance.student_id == student.id,
        Attendance.attendance_date == payload.attendance_date,
    ))
    created = row is None
    if row is None:
        row = Attendance(student_id=student.id, attendance_date=payload.attendance_date,
                         attendance_time=payload.attendance_time, status=payload.status,
                         verification_method="MANUAL", kiosk_id=None)
        db.add(row)
    else:
        row.attendance_time = payload.attendance_time
        row.status = payload.status
        row.verification_method = "MANUAL"
        row.kiosk_id = None
    db.flush()
    notify(db, student.user_id, "ATTENDANCE_RECORDED", "Attendance updated",
           f"{payload.status.value.title()} on {payload.attendance_date.strftime('%d %b %Y')} at {payload.attendance_time.strftime('%I:%M %p')}.")
    audit(db, actor.id, "ATTENDANCE_MARKED" if created else "ATTENDANCE_UPDATED", "attendance", row.id,
          {"student_id": student.id, "date": str(payload.attendance_date), "status": payload.status.value})
    db.commit(); db.refresh(row)
    return {"message": "Attendance saved", "id": row.id, "created": created,
            "student": student.user.name, "date": row.attendance_date,
            "time": row.attendance_time.strftime("%I:%M %p"), "status": row.status.value}


@router.get("/attendance/today")
def attendance_today(
    status: AttendanceStatus | None = None, room: int | None = Query(None, ge=0, le=430),
    q: str | None = None, attendance_date: date | None = Query(None, alias="date"),
    limit: int = Query(50, ge=1, le=300), db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.ADMIN, Role.WARDEN)),
):
    hostel_id = room_scope_for(user) or 1
    selected_date = attendance_date or today_ist()
    query = select(Attendance).join(Attendance.student).join(Student.user).outerjoin(Student.bed).outerjoin(Bed.room).where(
        Student.hostel_id == hostel_id, Attendance.attendance_date == selected_date)
    if status: query = query.where(Attendance.status == status)
    if room is not None: query = query.where(Room.room_number == room)
    if q:
        term = f"%{q.strip()}%"
        query = query.where(or_(User.name.ilike(term), Student.roll_no.ilike(term), Student.student_id.ilike(term)))
    rows = db.scalars(query.options(joinedload(Attendance.student).joinedload(Student.user),
                                    joinedload(Attendance.student).joinedload(Student.bed).joinedload(Bed.room))
                      .order_by(Attendance.attendance_time.desc()).limit(limit)).unique().all()
    return [{"id": a.id, "student_id": a.student.id, "name": a.student.user.name, "roll_no": a.student.roll_no,
             "room": a.student.bed.room.room_number if a.student.bed else None,
             "date": a.attendance_date, "time": a.attendance_time.strftime("%I:%M %p"), "status": a.status.value,
             "verification_method": a.verification_method} for a in rows]


@router.get("/student/profile")
def own_student_profile(db: Session = Depends(get_db), user: User = Depends(require_roles(Role.STUDENT))):
    return student_row(user.student, private=True)


@router.get("/student/attendance")
def own_attendance(db: Session = Depends(get_db), user: User = Depends(require_roles(Role.STUDENT))):
    rows = db.scalars(select(Attendance).where(Attendance.student_id == user.student.id)
                      .order_by(Attendance.attendance_date.desc()).limit(180)).all()
    present = sum(1 for r in rows if r.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE))
    return {"overall": round(present * 100 / len(rows), 1) if rows else 0,
            "present": sum(1 for r in rows if r.status == AttendanceStatus.PRESENT),
            "absent": sum(1 for r in rows if r.status == AttendanceStatus.ABSENT),
            "late": sum(1 for r in rows if r.status == AttendanceStatus.LATE),
            "history": [{"date": r.attendance_date, "time": r.attendance_time.strftime("%I:%M %p"), "status": r.status.value} for r in rows]}


@router.get("/hostel/timings")
def get_timings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    hostel_id = room_scope_for(user) or 1
    rows = db.scalars(select(HostelTiming).where(HostelTiming.hostel_id == hostel_id).order_by(HostelTiming.sort_order)).all()
    return [{"id": r.id, "key": r.key, "label": r.label, "value": r.value, "updated_at": r.updated_at} for r in rows]


@router.patch("/hostel/timings/{timing_id}")
def update_timing(timing_id: int, payload: TimingUpdate, db: Session = Depends(get_db), actor: User = Depends(require_roles(Role.ADMIN, Role.WARDEN))):
    row = db.get(HostelTiming, timing_id)
    if not row: raise HTTPException(404, "Timing not found")
    enforce_hostel_scope(actor, row.hostel_id)
    old = row.value; row.value = payload.value; row.updated_by = actor.id
    audit(db, actor.id, "HOSTEL_TIMING_UPDATED", "timing", row.id, {"old": old, "new": row.value})
    db.commit()
    return {"message": "Timing updated", "id": row.id, "value": row.value}


@router.get("/wardens")
def warden_directory(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    hostel_id = room_scope_for(user) or 1
    rows = db.scalars(select(Warden).where(Warden.hostel_id == hostel_id).options(joinedload(Warden.user))).all()
    return [{"name": w.user.name, "designation": w.designation, "phone": w.user.phone,
             "availability": w.availability} for w in rows if w.user.status == AccountStatus.ACTIVE]


@router.get("/notices")
def list_notices(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    hostel_id = room_scope_for(user) or 1
    rows = db.scalars(select(Notice).where(Notice.hostel_id == hostel_id, Notice.is_active.is_(True))
                      .order_by(Notice.published_at.desc()).limit(50)).all()
    return [{"id": n.id, "title": n.title, "message": n.message, "priority": n.priority,
             "published_at": n.published_at, "expires_at": n.expires_at} for n in rows]


@router.post("/notices", status_code=201)
def create_notice(payload: NoticeCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles(Role.ADMIN, Role.WARDEN))):
    enforce_hostel_scope(actor, payload.hostel_id)
    row = Notice(**payload.model_dump(), published_by=actor.id)
    db.add(row); db.flush(); audit(db, actor.id, "NOTICE_PUBLISHED", "notice", row.id)
    db.commit(); db.refresh(row)
    return {"id": row.id, "title": row.title, "message": row.message, "priority": row.priority, "published_at": row.published_at}


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id)
                      .order_by(Notification.created_at.desc()).limit(50)).all()
    return [{"id": n.id, "type": n.type, "title": n.title, "message": n.message,
             "is_read": n.is_read, "created_at": n.created_at} for n in rows]
