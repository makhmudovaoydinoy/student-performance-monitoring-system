from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import commit_or_409, get_current_user, require_admin
from ..models import Attendance, Enrollment, Grade, RiskAssessment, Student, Subject, User
from ..schemas import StudentIn
from ..services.calculator import attendance_rate, to_percent, weighted_average
from ..services.queries import rows_to_dicts, scope_condition, student_risk_select
from ..services.risk_service import assess_student

router = APIRouter(prefix="/api/students", tags=["Talabalar"])


def _visible_student(db: Session, user: User, student_id: int) -> dict:
    stmt = student_risk_select().where(Student.id == student_id)
    cond = scope_condition(db, user, Student.id)
    if cond is not None:
        stmt = stmt.where(cond)
    row = db.execute(stmt).first()
    if not row:
        raise HTTPException(404, "Talaba topilmadi yoki sizga ruxsat yo'q")
    return dict(row._mapping)


@router.get("")
def list_students(
    q: Optional[str] = None,
    group_id: Optional[int] = None,
    risk_level: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = student_risk_select()
    cond = scope_condition(db, user, Student.id)
    if cond is not None:
        stmt = stmt.where(cond)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(Student.full_name.ilike(like) | Student.student_code.ilike(like))
    if group_id:
        stmt = stmt.where(Student.group_id == group_id)
    if risk_level:
        stmt = stmt.where(RiskAssessment.risk_level == risk_level.upper())
    stmt = stmt.order_by(Student.full_name).offset(skip).limit(limit)
    return rows_to_dicts(db.execute(stmt).all())


@router.post("", status_code=201)
def create_student(data: StudentIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    student = Student(**data.model_dump())
    db.add(student)
    commit_or_409(db, "Talaba kodi allaqachon mavjud yoki guruh noto'g'ri")
    return {"id": student.id, **data.model_dump(mode="json")}


@router.put("/{student_id}")
def update_student(student_id: int, data: StudentIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(404, "Talaba topilmadi")
    for k, v in data.model_dump().items():
        setattr(student, k, v)
    commit_or_409(db, "Talaba kodi allaqachon mavjud yoki guruh noto'g'ri")
    return {"id": student.id, **data.model_dump(mode="json")}


@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(404, "Talaba topilmadi")
    db.delete(student)
    commit_or_409(db)
    return {"detail": "O'chirildi"}


@router.get("/{student_id}")
def student_detail(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    info = _visible_student(db, user, student_id)
    enrollments = db.execute(
        select(Enrollment.id, Subject.id.label("subject_id"), Subject.code, Subject.name)
        .join(Subject, Subject.id == Enrollment.subject_id)
        .where(Enrollment.student_id == student_id)
        .order_by(Subject.name)
    ).all()
    ids = [e.id for e in enrollments]
    grades, attendance = [], []
    if ids:
        grades = db.execute(
            select(Grade.id, Grade.enrollment_id, Grade.grade_type, Grade.score, Grade.max_score, Grade.graded_at, Grade.comment)
            .where(Grade.enrollment_id.in_(ids)).order_by(Grade.graded_at, Grade.id)
        ).all()
        attendance = db.execute(
            select(Attendance.enrollment_id, Attendance.status).where(Attendance.enrollment_id.in_(ids))
        ).all()
    subjects = []
    for e in enrollments:
        g = [(x.grade_type, x.score, x.max_score) for x in grades if x.enrollment_id == e.id]
        a = [x.status for x in attendance if x.enrollment_id == e.id]
        subjects.append({
            "subject_id": e.subject_id, "code": e.code, "name": e.name,
            "avg_score": weighted_average(g), "attendance_rate": attendance_rate(a), "grades_count": len(g),
        })
    grade_list = []
    names = {e.id: e.name for e in enrollments}
    for x in grades:
        grade_list.append({
            "id": x.id, "subject": names[x.enrollment_id], "grade_type": x.grade_type, "score": x.score,
            "max_score": x.max_score, "percent": round(to_percent(x.score, x.max_score), 1),
            "graded_at": x.graded_at, "comment": x.comment,
        })
    history = db.execute(
        select(RiskAssessment.calculated_at, RiskAssessment.risk_score, RiskAssessment.risk_level,
               RiskAssessment.avg_score, RiskAssessment.attendance_rate)
        .where(RiskAssessment.student_id == student_id).order_by(RiskAssessment.id)
    ).all()
    return {**info, "subjects": subjects, "grades": grade_list, "risk_history": rows_to_dicts(history)}
