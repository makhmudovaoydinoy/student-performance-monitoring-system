from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import commit_or_409, require_admin
from ..models import Teacher, User
from ..schemas import UserCreate, UserOut
from ..security import hash_password

router = APIRouter(prefix="/api/users", tags=["Foydalanuvchilar (ADMIN)"])


@router.get("", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return list(db.scalars(select(User).order_by(User.id)))


@router.post("", response_model=UserOut, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = User(
        username=data.username, email=data.email, password_hash=hash_password(data.password),
        full_name=data.full_name, role=data.role,
    )
    db.add(user)
    db.flush()
    if data.role == "TEACHER":
        db.add(Teacher(user_id=user.id, department=data.department, phone=data.phone))
    commit_or_409(db, "Bunday login yoki email allaqachon mavjud")
    return user


@router.delete("/{user_id}")
def deactivate_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Foydalanuvchi topilmadi")
    if user.id == admin.id:
        raise HTTPException(400, "O'zingizni o'chira olmaysiz")
    user.is_active = False
    db.commit()
    return {"detail": "Foydalanuvchi faolsizlantirildi"}
