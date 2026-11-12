"""Risk hisoblash oqimi: ma'lumot yig'ish -> hisoblash -> saqlash -> xabarnoma."""
import logging
from typing import Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Attendance, Enrollment, Grade, RiskAssessment, Student, utcnow
from . import notifier
from .calculator import attendance_rate, to_percent, trend_score, weighted_average
from .risk import compute_risk, should_notify

log = logging.getLogger("risk")


def collect_metrics(db: Session, student_id: int):
    enrollment_ids = select(Enrollment.id).where(Enrollment.student_id == student_id)
    grade_rows = db.execute(
        select(Grade.grade_type, Grade.score, Grade.max_score)
        .where(Grade.enrollment_id.in_(enrollment_ids))
        .order_by(Grade.graded_at, Grade.id)
    ).all()
    statuses = list(db.scalars(select(Attendance.status).where(Attendance.enrollment_id.in_(enrollment_ids))))
    grades = [(r.grade_type, r.score, r.max_score) for r in grade_rows]
    avg = weighted_average(grades)
    att = attendance_rate(statuses)
    trend = trend_score([to_percent(s, m) for _, s, m in grades])
    return avg, att, trend


def assess_student(db: Session, student_id: int, notify: bool = True) -> RiskAssessment:
    avg, att, trend = collect_metrics(db, student_id)
    result = compute_risk(avg, att, trend)
    prev = db.scalar(
        select(RiskAssessment).where(RiskAssessment.student_id == student_id).order_by(RiskAssessment.id.desc()).limit(1)
    )
    prev_level = prev.risk_level if prev else None
    now = utcnow()
    if prev and prev.risk_level == result.risk_level and prev.calculated_at.date() == now.date():
        prev.avg_score, prev.attendance_rate, prev.trend_score = avg, att, trend
        prev.risk_score, prev.calculated_at = result.risk_score, now
        assessment = prev
    else:
        assessment = RiskAssessment(
            student_id=student_id, avg_score=avg, attendance_rate=att, trend_score=trend,
            risk_score=result.risk_score, risk_level=result.risk_level, calculated_at=now,
        )
        db.add(assessment)
    db.flush()
    if notify and should_notify(prev_level, result.risk_level):
        student = db.get(Student, student_id)
        notifier.notify_risk(db, student, assessment)
    db.flush()
    return assessment


def assess_all(db: Session, notify: bool = True) -> Dict[str, int]:
    ids = list(db.scalars(select(Student.id).where(Student.status == "ACTIVE")))
    counts: Dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for sid in ids:
        counts[assess_student(db, sid, notify).risk_level] += 1
    db.commit()
    log.info("Barcha talabalar qayta baholandi: %s", counts)
    return {"students": len(ids), **counts}
