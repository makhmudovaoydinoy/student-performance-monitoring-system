"""Dashboard statistikasi (grafiklar uchun)."""
from collections import defaultdict
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Group, Notification, RiskAssessment, Student, Subject, User, utcnow
from ..services.queries import scope_condition, student_risk_select, rows_to_dicts

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _avg(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 2) if values else None


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cond = scope_condition(db, user, Student.id)
    stmt = student_risk_select()
    if cond is not None:
        stmt = stmt.where(cond)
    rows = rows_to_dicts(db.execute(stmt).all())

    distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "NO_DATA": 0}
    by_group = defaultdict(list)
    for r in rows:
        distribution[r["risk_level"] or "NO_DATA"] += 1
        by_group[r["group_name"]].append(r)
    groups = [
        {
            "group": name,
            "students": len(items),
            "avg_score": _avg([i["avg_score"] for i in items]),
            "avg_attendance": _avg([i["attendance_rate"] for i in items]),
            "avg_risk": _avg([i["risk_score"] for i in items]),
            "at_risk": sum(1 for i in items if i["risk_level"] in ("HIGH", "CRITICAL")),
        }
        for name, items in sorted(by_group.items())
    ]
    top = sorted((r for r in rows if r["risk_score"] is not None), key=lambda r: r["risk_score"], reverse=True)[:5]

    since = utcnow() - timedelta(days=180)
    trend_stmt = select(RiskAssessment.calculated_at, RiskAssessment.risk_score).where(RiskAssessment.calculated_at >= since)
    if cond is not None:
        trend_stmt = trend_stmt.where(scope_condition(db, user, RiskAssessment.student_id))
    monthly = defaultdict(list)
    for ts, score in db.execute(trend_stmt).all():
        monthly[ts.strftime("%Y-%m")].append(score)
    risk_trend = [{"month": m, "avg_risk": _avg(v)} for m, v in sorted(monthly.items())]

    unread = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.recipient_user_id == user.id, Notification.channel == "IN_APP", Notification.is_read.is_(False)
        )
    )
    return {
        "totals": {
            "students": len(rows),
            "groups": len(groups),
            "subjects": db.scalar(select(func.count(Subject.id))) or 0,
            "at_risk": distribution["HIGH"] + distribution["CRITICAL"],
            "avg_score": _avg([r["avg_score"] for r in rows]),
            "avg_attendance": _avg([r["attendance_rate"] for r in rows]),
            "unread_notifications": unread or 0,
        },
        "distribution": distribution,
        "groups": groups,
        "risk_trend": risk_trend,
        "top_risk": [
            {k: r[k] for k in ("id", "student_code", "full_name", "group_name", "risk_score", "risk_level")} for r in top
        ],
    }
