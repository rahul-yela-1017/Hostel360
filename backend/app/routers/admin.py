from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import require_roles
from ..models import AccountStatus, AuditLog, Cook, Hostel, Role, User, Warden
from ..schemas import StaffCreate, StaffUpdate
from ..security import hash_password
from ..services import audit

router = APIRouter(prefix="/admin", tags=["Admin"])


def _staff_row(user: User) -> dict:
    detail = user.warden or user.cook
    return {
        "id": user.id, "name": user.name, "email": user.email, "phone": user.phone,
        "role": user.role.value, "status": user.status.value,
        "employee_id": getattr(detail, "employee_id", None),
        "designation": getattr(detail, "designation", None) or getattr(detail, "assigned_mess", None),
        "availability": getattr(detail, "availability", None),
        "hostel_id": getattr(detail, "hostel_id", None),
        "created_at": user.created_at,
    }


def _create_staff(payload: StaffCreate, role: Role, actor: User, db: Session):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(409, "An account with that email already exists")
    if not db.get(Hostel, payload.hostel_id):
        raise HTTPException(404, "Hostel not found")
    user = User(name=payload.name, email=payload.email.lower(), phone=payload.phone,
                password_hash=hash_password(payload.temporary_password), role=role,
                status=AccountStatus.ACTIVE, must_change_password=True)
    db.add(user)
    db.flush()
    if role == Role.WARDEN:
        detail = Warden(user_id=user.id, employee_id=payload.employee_id, hostel_id=payload.hostel_id,
                        designation=payload.designation or "Warden", availability=payload.assigned_area or "Day Shift")
    else:
        detail = Cook(user_id=user.id, employee_id=payload.employee_id, hostel_id=payload.hostel_id,
                      assigned_mess=payload.assigned_area or "Main Mess")
    db.add(detail)
    audit(db, actor.id, f"{role.value}_CREATED", role.value.lower(), user.id)
    db.commit()
    db.refresh(user)
    return _staff_row(user)


@router.post("/wardens", status_code=201)
def create_warden(payload: StaffCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles(Role.ADMIN))):
    return _create_staff(payload, Role.WARDEN, actor, db)


@router.post("/cooks", status_code=201)
def create_cook(payload: StaffCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles(Role.ADMIN))):
    return _create_staff(payload, Role.COOK, actor, db)


@router.get("/wardens")
def list_wardens(db: Session = Depends(get_db), _: User = Depends(require_roles(Role.ADMIN))):
    return [_staff_row(u) for u in db.scalars(select(User).where(User.role == Role.WARDEN).order_by(User.name)).all()]


@router.get("/cooks")
def list_cooks(db: Session = Depends(get_db), _: User = Depends(require_roles(Role.ADMIN))):
    return [_staff_row(u) for u in db.scalars(select(User).where(User.role == Role.COOK).order_by(User.name)).all()]


@router.patch("/staff/{user_id}")
def update_staff(user_id: int, payload: StaffUpdate, db: Session = Depends(get_db), actor: User = Depends(require_roles(Role.ADMIN))):
    user = db.get(User, user_id)
    if not user or user.role not in (Role.WARDEN, Role.COOK):
        raise HTTPException(404, "Staff account not found")
    values = payload.model_dump(exclude_unset=True)
    for field in ("name", "phone", "status"):
        if field in values:
            setattr(user, field, values[field])
    if user.warden:
        if "designation" in values: user.warden.designation = values["designation"]
        if "assigned_area" in values: user.warden.availability = values["assigned_area"]
    if user.cook and "assigned_area" in values:
        user.cook.assigned_mess = values["assigned_area"]
    audit(db, actor.id, "STAFF_UPDATED", "user", user.id, values)
    db.commit()
    return _staff_row(user)


@router.delete("/staff/{user_id}", status_code=204)
def disable_staff(user_id: int, db: Session = Depends(get_db), actor: User = Depends(require_roles(Role.ADMIN))):
    user = db.get(User, user_id)
    if not user or user.role not in (Role.WARDEN, Role.COOK):
        raise HTTPException(404, "Staff account not found")
    user.status = AccountStatus.DISABLED
    audit(db, actor.id, "STAFF_DISABLED", "user", user.id)
    db.commit()


@router.get("/audit-logs")
def audit_logs(limit: int = Query(50, ge=1, le=250), db: Session = Depends(get_db), _: User = Depends(require_roles(Role.ADMIN))):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)).all()
    return [{"id": r.id, "user_id": r.user_id, "action": r.action, "resource": r.resource,
             "resource_id": r.resource_id, "details": r.details, "timestamp": r.timestamp} for r in rows]
