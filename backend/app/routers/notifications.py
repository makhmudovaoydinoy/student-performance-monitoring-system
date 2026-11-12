from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Notification, Student, User
from ..services.queries import rows_to_dicts

router = APIRouter(prefix="/api/notifications", tags=["Xabarnomalar"])


@router.get("")
def my_notifications(unread_only: bool = False, limit: int = 100, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = (
        select(Notification.id, Notification.title, Notification.message, Notification.channel, Notification.status,
               Notification.is_read, Notification.created_at, Notification.student_id,
               Student.full_name.label("student_name"))
        .outerjoin(Student, Student.id == Notification.student_id)
        .where(Notification.recipient_user_id == user.id, Notification.channel == "IN_APP")
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    return rows_to_dicts(db.execute(stmt.order_by(Notification.id.desc()).limit(min(limit, 500))).all())


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.recipient_user_id == user.id, Notification.channel == "IN_APP", Notification.is_read.is_(False)
        )
    )
    return {"count": n or 0}


@router.post("/read-all")
def read_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.execute(update(Notification).where(Notification.recipient_user_id == user.id).values(is_read=True))
    db.commit()
    return {"detail": "Hammasi o'qilgan deb belgilandi"}


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = db.get(Notification, notification_id)
    if not n or n.recipient_user_id != user.id:
        raise HTTPException(404, "Xabarnoma topilmadi")
    n.is_read = True
    db.commit()
    return {"detail": "O'qilgan"}
