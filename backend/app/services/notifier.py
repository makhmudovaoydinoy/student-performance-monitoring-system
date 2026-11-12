"""Notification moduli: xabarnoma yaratish va (ixtiyoriy) email yuborish."""
import logging
import smtplib
from email.message import EmailMessage
from typing import List, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Enrollment, Group, Notification, RiskAssessment, Student, Subject, Teacher, User, utcnow

log = logging.getLogger("notifier")
LEVEL_LABEL = {"LOW": "PAST", "MEDIUM": "O'RTACHA", "HIGH": "YUQORI", "CRITICAL": "KRITIK"}


def _fmt(value) -> str:
    return "—" if value is None else f"{value:g}"


def recipients_for(db: Session, student: Student, level: str) -> Set[int]:
    """Talabaning fan o'qituvchilari + guruh kuratori; KRITIK bo'lsa (yoki hech kim bo'lmasa) adminlar ham."""
    ids: Set[int] = set(
        db.scalars(
            select(Teacher.user_id)
            .join(Subject, Subject.teacher_id == Teacher.id)
            .join(Enrollment, Enrollment.subject_id == Subject.id)
            .where(Enrollment.student_id == student.id)
            .distinct()
        )
    )
    curator = db.scalar(
        select(Teacher.user_id).join(Group, Group.curator_id == Teacher.id).where(Group.id == student.group_id)
    )
    if curator:
        ids.add(curator)
    if level == "CRITICAL" or not ids:
        ids.update(db.scalars(select(User.id).where(User.role == "ADMIN", User.is_active.is_(True))))
    return ids


def send_email(to_addr: str, subject: str, body: str) -> bool:
    if not settings.smtp_host:
        return False
    try:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, to_addr, subject
        msg.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception as exc:  # tarmoq xatosi tizimni to'xtatmasligi kerak
        log.warning("Email yuborilmadi (%s): %s", to_addr, exc)
        return False


def notify_risk(db: Session, student: Student, assessment: RiskAssessment) -> List[Notification]:
    label = LEVEL_LABEL.get(assessment.risk_level, assessment.risk_level)
    title = f"Xavf darajasi {label}: {student.full_name}"
    message = (
        f"{student.full_name} ({student.student_code}) talabaning xavf darajasi {label} ga yetdi. "
        f"O'rtacha ball: {_fmt(assessment.avg_score)}%, davomat: {_fmt(assessment.attendance_rate)}%, "
        f"xavf bali: {_fmt(assessment.risk_score)}. Iltimos, talaba bilan suhbat o'tkazing."
    )
    created: List[Notification] = []
    for uid in recipients_for(db, student, assessment.risk_level):
        user = db.get(User, uid)
        if not user or not user.is_active:
            continue
        created.append(Notification(
            recipient_user_id=uid, student_id=student.id, risk_assessment_id=assessment.id,
            title=title, message=message, channel="IN_APP", status="SENT", sent_at=utcnow(),
        ))
        if settings.smtp_host and user.email:
            ok = send_email(user.email, title, message)
            created.append(Notification(
                recipient_user_id=uid, student_id=student.id, risk_assessment_id=assessment.id,
                title=title, message=message, channel="EMAIL",
                status="SENT" if ok else "FAILED", sent_at=utcnow() if ok else None,
            ))
    db.add_all(created)
    log.info("Xabarnoma yaratildi: talaba=%s daraja=%s soni=%d", student.student_code, assessment.risk_level, len(created))
    return created
