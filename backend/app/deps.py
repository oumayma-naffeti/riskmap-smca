"""Dépendances FastAPI : qui est connecté ? a-t-il le droit ?"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        username = decode_token(token).get("sub")
    except jwt.PyJWTError:
        raise error
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        raise error
    return user  # le rôle est relu en base : un changement de rôle s'applique tout de suite


def require_role(*roles: str):
    """Usage : Depends(require_role("admin", "analyste"))"""
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits insuffisants")
        return user
    return checker
