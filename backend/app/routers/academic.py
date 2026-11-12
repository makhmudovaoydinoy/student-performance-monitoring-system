"""Guruhlar, fanlar, o'qituvchilar va enrollment (talaba-fan bog'lanishi)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import commit_or_409, get_current_user, require_admin
from ..models import Enrollment, Group, Student, Subject, Teacher, User
from ..schemas import EnrollmentIn, GroupEnrollIn, GroupIn, SubjectIn
from ..services.queries import can_manage_subject, get_teacher, rows_to_dicts

router = APIRouter(prefix="/api", tags=["Akademik"])


# ---------- O'qituvchilar ----------
@router.get("/teachers")
def list_teachers(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.execute(
        select(Teacher.id, User.full_name, Teacher.department).join(User, User.id == Teacher.user_id).order_by(User.full_name)
    ).all()
    return rows_to_dicts(rows)


# ---------- Guruhlar ----------
@router.get("/groups")
def list_groups(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    counts = dict(db.execute(select(Student.group_id, func.count(Student.id)).group_by(Student.group_id)).all())
    rows = db.execute(
        select(Group.id, Group.name, Group.course_year, Group.specialty, Group.curator_id, User.full_name.label("curator_name"))
        .outerjoin(Teacher, Teacher.id == Group.curator_id)
        .outerjoin(User, User.id == Teacher.user_id)
        .order_by(Group.name)
    ).all()
    result = rows_to_dicts(rows)
    for r in result:
        r["student_count"] = counts.get(r["id"], 0)
    return result


@router.post("/groups", status_code=201)
def create_group(data: GroupIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    group = Group(**data.model_dump())
    db.add(group)
    commit_or_409(db, "Bunday guruh nomi mavjud yoki kurator noto'g'ri")
    return {"id": group.id, **data.model_dump()}


@router.put("/groups/{group_id}")
def update_group(group_id: int, data: GroupIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(404, "Guruh topilmadi")
    for k, v in data.model_dump().items():
        setattr(group, k, v)
    commit_or_409(db, "Bunday guruh nomi mavjud yoki kurator noto'g'ri")
    return {"id": group.id, **data.model_dump()}


@router.delete("/groups/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(404, "Guruh topilmadi")
    db.delete(group)
    commit_or_409(db, "Guruhda talabalar bor, avval ularni boshqa guruhga o'tkazing")
    return {"detail": "O'chirildi"}


# ---------- Fanlar ----------
@router.get("/subjects")
def list_subjects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = (
        select(Subject.id, Subject.code, Subject.name, Subject.credits, Subject.semester, Subject.teacher_id,
               User.full_name.label("teacher_name"))
        .outerjoin(Teacher, Teacher.id == Subject.teacher_id)
        .outerjoin(User, User.id == Teacher.user_id)
        .order_by(Subject.code)
    )
    if user.role == "TEACHER":
        teacher = get_teacher(db, user)
        stmt = stmt.where(Subject.teacher_id == (teacher.id if teacher else -1))
    return rows_to_dicts(db.execute(stmt).all())


@router.post("/subjects", status_code=201)
def create_subject(data: SubjectIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    subject = Subject(**data.model_dump())
    db.add(subject)
    commit_or_409(db, "Bunday fan kodi mavjud yoki o'qituvchi noto'g'ri")
    return {"id": subject.id, **data.model_dump()}


@router.put("/subjects/{subject_id}")
def update_subject(subject_id: int, data: SubjectIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    subject = db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(404, "Fan topilmadi")
    for k, v in data.model_dump().items():
        setattr(subject, k, v)
    commit_or_409(db, "Bunday fan kodi mavjud yoki o'qituvchi noto'g'ri")
    return {"id": subject.id, **data.model_dump()}


@router.delete("/subjects/{subject_id}")
def delete_subject(subject_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    subject = db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(404, "Fan topilmadi")
    db.delete(subject)
    commit_or_409(db)
    return {"detail": "O'chirildi"}


@router.get("/subjects/{subject_id}/enrollments")
def subject_enrollments(subject_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    subject = db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(404, "Fan topilmadi")
    if not can_manage_subject(db, user, subject):
        raise HTTPException(403, "Bu fan sizga biriktirilmagan")
    rows = db.execute(
        select(Enrollment.id.label("enrollment_id"), Student.id.label("student_id"), Student.student_code,
               Student.full_name, Group.name.label("group_name"))
        .join(Student, Student.id == Enrollment.student_id)
        .join(Group, Group.id == Student.group_id)
        .where(Enrollment.subject_id == subject_id)
        .order_by(Student.full_name)
    ).all()
    return rows_to_dicts(rows)


# ---------- Enrollment ----------
@router.post("/enrollments", status_code=201)
def create_enrollment(data: EnrollmentIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    enrollment = Enrollment(student_id=data.student_id, subject_id=data.subject_id)
    db.add(enrollment)
    commit_or_409(db, "Talaba bu fanga allaqachon yozilgan yoki id noto'g'ri")
    return {"id": enrollment.id, **data.model_dump()}


@router.post("/enrollments/group")
def enroll_group(data: GroupEnrollIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if not db.get(Group, data.group_id) or not db.get(Subject, data.subject_id):
        raise HTTPException(404, "Guruh yoki fan topilmadi")
    student_ids = list(db.scalars(select(Student.id).where(Student.group_id == data.group_id, Student.status == "ACTIVE")))
    already = set(db.scalars(select(Enrollment.student_id).where(Enrollment.subject_id == data.subject_id)))
    added = 0
    for sid in student_ids:
        if sid not in already:
            db.add(Enrollment(student_id=sid, subject_id=data.subject_id))
            added += 1
    db.commit()
    return {"added": added, "skipped": len(student_ids) - added}


@router.delete("/enrollments/{enrollment_id}")
def delete_enrollment(enrollment_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    enrollment = db.get(Enrollment, enrollment_id)
    if not enrollment:
        raise HTTPException(404, "Yozuv topilmadi")
    db.delete(enrollment)
    db.commit()
    return {"detail": "O'chirildi"}
