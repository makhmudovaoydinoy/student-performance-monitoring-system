"""Qayta ishlatiladigan so'rovlar: oxirgi risk, ko'rinish doirasi (scope)."""
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..models import Enrollment, Group, RiskAssessment, Student, Subject, Teacher, User


def student_risk_select():
    """Talaba + guruh nomi + oxirgi risk bahosi."""
    latest = (
        select(func.max(RiskAssessment.id).label("mid"), RiskAssessment.student_id.label("sid"))
        .group_by(RiskAssessment.student_id)
        .subquery()
    )
    return (
        select(
            Student.id, Student.student_code, Student.full_name, Student.email, Student.phone,
            Student.birth_date, Student.group_id, Group.name.label("group_name"), Student.status,
            RiskAssessment.risk_level, RiskAssessment.risk_score, RiskAssessment.avg_score,
            RiskAssessment.attendance_rate, RiskAssessment.calculated_at,
        )
        .join(Group, Group.id == Student.group_id)
        .outerjoin(latest, latest.c.sid == Student.id)
        .outerjoin(RiskAssessment, RiskAssessment.id == latest.c.mid)
    )


def rows_to_dicts(rows) -> list:
    return [dict(r._mapping) for r in rows]


def get_teacher(db: Session, user: User) -> Optional[Teacher]:
    return db.scalar(select(Teacher).where(Teacher.user_id == user.id))


def scope_condition(db: Session, user: User, student_id_column):
    """ADMIN uchun None (cheklov yo'q). TEACHER faqat o'z fanlariga yozilgan yoki
    o'zi kurator bo'lgan guruh talabalarini ko'radi."""
    if user.role == "ADMIN":
        return None
    if user.role == "STUDENT":
        return student_id_column == user.student_id
    teacher = get_teacher(db, user)
    tid = teacher.id if teacher else -1
    by_subject = (
        select(Enrollment.student_id)
        .join(Subject, Subject.id == Enrollment.subject_id)
        .where(Subject.teacher_id == tid)
    )
    by_group = select(Student.id).join(Group, Group.id == Student.group_id).where(Group.curator_id == tid)
    return or_(student_id_column.in_(by_subject), student_id_column.in_(by_group))


def can_manage_subject(db: Session, user: User, subject: Subject) -> bool:
    if user.role == "ADMIN":
        return True
    teacher = get_teacher(db, user)
    return bool(teacher and subject.teacher_id == teacher.id)
