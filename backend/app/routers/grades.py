"""Baholar va davomat kiritish. Har bir yozuvdan keyin risk avtomatik qayta hisoblanadi."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Attendance, Enrollment, Grade, Student, Subject, User
from ..schemas import AttendanceBulkIn, GradeIn
from ..services.queries import can_manage_subject, rows_to_dicts
from ..services.risk_service import assess_student

router = APIRouter(prefix="/api", tags=["Baho va davomat"])


def _enrollment_subject(db: Session, enrollment_id: int):
    row = db.execute(
        select(Enrollment, Subject).join(Subject, Subject.id == Enrollment.subject_id).where(Enrollment.id == enrollment_id)
    ).first()
    if not row:
        raise HTTPException(404, "Enrollment topilmadi")
    return row[0], row[1]


@router.post("/grades", status_code=201)
def add_grade(data: GradeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    enrollment, subject = _enrollment_subject(db, data.enrollment_id)
    if not can_manage_subject(db, user, subject):
        raise HTTPException(403, "Bu fan sizga biriktirilmagan")
    grade = Grade(
        enrollment_id=data.enrollment_id, grade_type=data.grade_type, score=data.score, max_score=data.max_score,
        graded_at=data.graded_at or date.today(), comment=data.comment, created_by=user.id,
    )
    db.add(grade)
    db.flush()
    risk = assess_student(db, enrollment.student_id)
    db.commit()
    return {"id": grade.id, "risk_level": risk.risk_level, "risk_score": risk.risk_score}


@router.get("/grades")
def list_grades(subject_id: int, limit: int = 100, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    subject = db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(404, "Fan topilmadi")
    if not can_manage_subject(db, user, subject):
        raise HTTPException(403, "Bu fan sizga biriktirilmagan")
    rows = db.execute(
        select(Grade.id, Student.full_name, Student.student_code, Grade.grade_type, Grade.score, Grade.max_score,
               Grade.graded_at, Grade.comment)
        .join(Enrollment, Enrollment.id == Grade.enrollment_id)
        .join(Student, Student.id == Enrollment.student_id)
        .where(Enrollment.subject_id == subject_id)
        .order_by(Grade.graded_at.desc(), Grade.id.desc())
        .limit(min(limit, 500))
    ).all()
    return rows_to_dicts(rows)


@router.delete("/grades/{grade_id}")
def delete_grade(grade_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    grade = db.get(Grade, grade_id)
    if not grade:
        raise HTTPException(404, "Baho topilmadi")
    enrollment, subject = _enrollment_subject(db, grade.enrollment_id)
    if not can_manage_subject(db, user, subject):
        raise HTTPException(403, "Bu fan sizga biriktirilmagan")
    db.delete(grade)
    db.flush()
    assess_student(db, enrollment.student_id)
    db.commit()
    return {"detail": "O'chirildi"}


@router.get("/attendance")
def get_attendance(subject_id: int, lesson_date: date, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    subject = db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(404, "Fan topilmadi")
    if not can_manage_subject(db, user, subject):
        raise HTTPException(403, "Bu fan sizga biriktirilmagan")
    rows = db.execute(
        select(Attendance.enrollment_id, Attendance.status, Attendance.note)
        .join(Enrollment, Enrollment.id == Attendance.enrollment_id)
        .where(Enrollment.subject_id == subject_id, Attendance.lesson_date == lesson_date)
    ).all()
    return rows_to_dicts(rows)


@router.post("/attendance/bulk")
def save_attendance(data: AttendanceBulkIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    subject = db.get(Subject, data.subject_id)
    if not subject:
        raise HTTPException(404, "Fan topilmadi")
    if not can_manage_subject(db, user, subject):
        raise HTTPException(403, "Bu fan sizga biriktirilmagan")
    valid = {e.id: e.student_id for e in db.scalars(select(Enrollment).where(Enrollment.subject_id == data.subject_id))}
    affected = set()
    saved = 0
    for rec in data.records:
        if rec.enrollment_id not in valid:
            raise HTTPException(400, f"Enrollment {rec.enrollment_id} bu fanga tegishli emas")
        existing = db.scalar(
            select(Attendance).where(Attendance.enrollment_id == rec.enrollment_id, Attendance.lesson_date == data.lesson_date)
        )
        if existing:
            existing.status, existing.note = rec.status, rec.note
        else:
            db.add(Attendance(enrollment_id=rec.enrollment_id, lesson_date=data.lesson_date, status=rec.status,
                              note=rec.note, created_by=user.id))
        affected.add(valid[rec.enrollment_id])
        saved += 1
    db.flush()
    for sid in affected:
        assess_student(db, sid)
    db.commit()
    return {"saved": saved, "students_reassessed": len(affected)}
