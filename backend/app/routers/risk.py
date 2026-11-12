"""Risk assessment: xavf guruhi, qayta hisoblash, tarix, CSV eksport, Cloud Scheduler endpointi."""
import csv
import hmac
import io
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import RiskAssessment, Student, User
from ..services.queries import rows_to_dicts, scope_condition, student_risk_select
from ..services.risk_service import assess_all, assess_student

router = APIRouter(prefix="/api/risk", tags=["Risk (erta ogohlantirish)"])


def _at_risk_rows(db: Session, user: User, level: Optional[str]):
    levels = [level.upper()] if level else ["HIGH", "CRITICAL"]
    stmt = student_risk_select().where(RiskAssessment.risk_level.in_(levels))
    cond = scope_condition(db, user, Student.id)
    if cond is not None:
        stmt = stmt.where(cond)
    return rows_to_dicts(db.execute(stmt.order_by(RiskAssessment.risk_score.desc())).all())


@router.get("/at-risk")
def at_risk(level: Optional[str] = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _at_risk_rows(db, user, level)


@router.get("/export.csv")
def export_csv(level: Optional[str] = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = _at_risk_rows(db, user, level)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["student_code", "full_name", "group", "avg_score", "attendance_rate", "risk_score", "risk_level"])
    for r in rows:
        writer.writerow([r["student_code"], r["full_name"], r["group_name"], r["avg_score"], r["attendance_rate"],
                         r["risk_score"], r["risk_level"]])
    return Response("\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=xavf_guruhi.csv"})


@router.get("/students/{student_id}/history")
def history(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cond = scope_condition(db, user, Student.id)
    stmt = select(Student.id).where(Student.id == student_id)
    if cond is not None:
        stmt = stmt.where(cond)
    if db.scalar(stmt) is None:
        raise HTTPException(404, "Talaba topilmadi yoki sizga ruxsat yo'q")
    rows = db.execute(
        select(RiskAssessment.id, RiskAssessment.calculated_at, RiskAssessment.avg_score, RiskAssessment.attendance_rate,
               RiskAssessment.trend_score, RiskAssessment.risk_score, RiskAssessment.risk_level)
        .where(RiskAssessment.student_id == student_id).order_by(RiskAssessment.id)
    ).all()
    return rows_to_dicts(rows)


@router.post("/students/{student_id}/recalculate")
def recalc_one(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cond = scope_condition(db, user, Student.id)
    stmt = select(Student.id).where(Student.id == student_id)
    if cond is not None:
        stmt = stmt.where(cond)
    if db.scalar(stmt) is None:
        raise HTTPException(404, "Talaba topilmadi yoki sizga ruxsat yo'q")
    a = assess_student(db, student_id)
    db.commit()
    return {"risk_level": a.risk_level, "risk_score": a.risk_score, "avg_score": a.avg_score,
            "attendance_rate": a.attendance_rate}


@router.post("/recalculate")
def recalc_all(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return assess_all(db)


@router.post("/scheduler-run")
def scheduler_run(x_scheduler_token: str = Header(default=""), db: Session = Depends(get_db)):
    """Cloud Scheduler har kecha chaqiradi. Header: X-Scheduler-Token."""
    if not settings.scheduler_token:
        raise HTTPException(503, "SCHEDULER_TOKEN sozlanmagan")
    if not hmac.compare_digest(x_scheduler_token, settings.scheduler_token):
        raise HTTPException(403, "Token noto'g'ri")
    return assess_all(db)
