import hmac
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from ..config import settings
from ..database import get_db
from ..deps import require_roles
from ..models import FaceEmbedding, Role, Student, User
from ..schemas import FaceEnrollRequest, KioskAttendanceRequest
from ..services import audit, cosine_similarity, decrypt_embedding, encrypt_embedding, record_attendance

router = APIRouter(prefix="/face", tags=["Face & Kiosk"])


def verify_kiosk(x_kiosk_key: str = Header(..., alias="X-Kiosk-Key")):
    if not hmac.compare_digest(x_kiosk_key, settings.kiosk_api_key):
        raise HTTPException(401, "Invalid kiosk credentials")


@router.post("/enroll")
def enroll_face(payload: FaceEnrollRequest, db: Session = Depends(get_db), actor: User = Depends(require_roles(Role.ADMIN, Role.WARDEN))):
    if payload.liveness_score < .85:
        raise HTTPException(422, "Liveness verification failed; face data was not saved")
    student = db.get(Student, payload.student_id)
    if not student: raise HTTPException(404, "Student not found")
    if actor.role == Role.WARDEN and actor.warden.hostel_id != student.hostel_id:
        raise HTTPException(403, "Student is outside your hostel scope")
    row = db.scalar(select(FaceEmbedding).where(FaceEmbedding.student_id == student.id))
    if row:
        row.encrypted_embedding = encrypt_embedding(payload.embedding)
        row.model_version = payload.model_version
    else:
        row = FaceEmbedding(student_id=student.id, encrypted_embedding=encrypt_embedding(payload.embedding),
                            model_version=payload.model_version)
        db.add(row)
    student.face_enrolled = True
    audit(db, actor.id, "FACE_ENROLLED", "student", student.id, {"model_version": payload.model_version})
    db.commit()
    return {"message": "Face registration completed", "student_id": student.id, "model_version": payload.model_version}


@router.post("/recognize", dependencies=[Depends(verify_kiosk)])
def recognize_and_record(payload: KioskAttendanceRequest, db: Session = Depends(get_db)):
    if payload.liveness_score < .85:
        raise HTTPException(422, "Liveness check failed")

    student = None
    confidence = None
    best_score, best_student_id = -1.0, None
    for face in db.scalars(select(FaceEmbedding)).all():
        score = cosine_similarity(payload.embedding, decrypt_embedding(face.encrypted_embedding))
        if score > best_score:
            best_score, best_student_id = score, face.student_id
    if best_score >= .72 and best_student_id:
        student = db.scalar(select(Student).where(Student.id == best_student_id).options(
            joinedload(Student.user), joinedload(Student.bed)))
        confidence = best_score
    if not student:
        raise HTTPException(404, "Face not recognized")

    attendance, created = record_attendance(db, student, payload.device_id, payload.liveness_score, payload.captured_at)
    bed = student.bed
    return {"result": "RECORDED" if created else "ALREADY_RECORDED",
            "message": "Attendance recorded" if created else "Attendance already recorded today.",
            "student": {"name": student.user.name, "room": bed.room.room_number if bed else None,
                        "bed": bed.bed_number if bed else None},
            "attendance": {"date": attendance.attendance_date, "time": attendance.attendance_time.strftime("%I:%M %p"),
                           "status": attendance.status.value},
            "confidence": confidence}
