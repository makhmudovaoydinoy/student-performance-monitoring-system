"""Autentifikatsiya va avtorizatsiya (RBAC) bog'liqliklari."""
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    exc = HTTPException(401, "Autentifikatsiya talab qilinadi", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise exc
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise exc
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Bu amal uchun ruxsat yo'q")
        return user

    return checker


require_admin = require_roles("ADMIN")


def commit_or_409(db: Session, message: str = "Ma'lumot allaqachon mavjud yoki bog'liq yozuvlar bor") -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, message)
