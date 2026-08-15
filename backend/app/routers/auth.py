from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import get_current_user
from ..models import AccountStatus, Role, User
from ..schemas import ChangePasswordRequest, InitialAdminCreate, LoginRequest, TokenResponse
from ..security import create_access_token, hash_password, verify_password
from ..services import audit

router = APIRouter(prefix="/auth", tags=["Authentication"])


def serialize_user(user: User) -> dict:
    profile = {"id": user.id, "name": user.name, "email": user.email, "phone": user.phone,
               "role": user.role.value, "status": user.status.value, "must_change_password": user.must_change_password}
    if user.student:
        profile.update({"student_id": user.student.id, "roll_no": user.student.roll_no,
                        "room": user.student.bed.room.room_number if user.student.bed else None,
                        "bed": user.student.bed.bed_number if user.student.bed else None})
    return profile


@router.get("/setup/status")
def setup_status(db: Session = Depends(get_db)):
    admins = db.scalar(select(func.count(User.id)).where(User.role == Role.ADMIN)) or 0
    return {"setup_required": admins == 0, "hostel_name": "Malla Reddy Boys Hostel"}


@router.post("/setup/admin", status_code=201)
def create_initial_admin(payload: InitialAdminCreate, db: Session = Depends(get_db)):
    # This endpoint permanently closes as soon as the first Admin exists.
    if (db.scalar(select(func.count(User.id)).where(User.role == Role.ADMIN)) or 0) > 0:
        raise HTTPException(409, "Initial setup has already been completed")
    user = User(name=payload.name.strip(), email=payload.email.lower(), phone=payload.phone,
                password_hash=hash_password(payload.password), role=Role.ADMIN,
                status=AccountStatus.ACTIVE, must_change_password=False)
    db.add(user)
    try:
        db.flush()
        audit(db, user.id, "INITIAL_ADMIN_CREATED", "user", user.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Initial setup was completed by another request") from exc
    return {"message": "Administrator account created. You can now sign in."}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    if user.status != AccountStatus.ACTIVE:
        raise HTTPException(403, "This account has been disabled")
    return TokenResponse(access_token=create_access_token(user.id), user=serialize_user(user))


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return serialize_user(user)


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(400, "New password must be different")
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    audit(db, user.id, "PASSWORD_CHANGED", "user", user.id)
    db.commit()
    return {"message": "Password changed successfully"}
