from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import StudentPrincipal, get_current_user
from ..models import Student, StudentAccount, User
from ..schemas import PasswordChange, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == form.username))
    if user:
        if not user.is_active or not verify_password(form.password, user.password_hash):
            raise HTTPException(401, "Login yoki parol noto'g'ri", headers={"WWW-Authenticate": "Bearer"})
        return TokenOut(access_token=create_access_token(user.id, user.role), user=UserOut.model_validate(user))
    account = db.scalar(select(StudentAccount).where(StudentAccount.username == form.username))
    student = db.get(Student, account.student_id) if account else None
    if (not account or not account.is_active or not student or student.status != "ACTIVE"
            or not verify_password(form.password, account.password_hash)):
        raise HTTPException(401, "Login yoki parol noto'g'ri", headers={"WWW-Authenticate": "Bearer"})
    principal = StudentPrincipal(id=account.id, username=account.username, email=student.email or "",
        full_name=student.full_name, role="STUDENT", is_active=True, student_id=student.id)
    return TokenOut(access_token=create_access_token(account.id, "STUDENT"), user=UserOut.model_validate(principal))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password")
def change_password(data: PasswordChange, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(400, "Eski parol noto'g'ri")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"detail": "Parol yangilandi"}
