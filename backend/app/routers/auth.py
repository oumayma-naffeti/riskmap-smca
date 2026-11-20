from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import SetupAdmin, Token, UserOut
from ..security import DUMMY_HASH, create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/setup", response_model=UserOut, status_code=201)
def setup_first_admin(data: SetupAdmin, db: Session = Depends(get_db)):
    """Crée le premier administrateur. Ne fonctionne qu'une fois, tant qu'il n'y a aucun utilisateur."""
    if db.scalar(select(func.count()).select_from(User)) > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "L'installation initiale est déjà faite")
    user = User(username=data.username, password_hash=hash_password(data.password), role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == form.username))
    ok = verify_password(form.password, user.password_hash if user else DUMMY_HASH)
    if not user or not ok:
        # commit AVANT le raise : sinon l'exception annule la transaction et la trace disparaît
        log_action(db, user, "échec connexion", "auth", None,
                   f"identifiant essayé : {form.username[:50]}")
        db.commit()
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    log_action(db, user, "connexion", "auth", user.id)
    db.commit()
    return Token(access_token=create_access_token(user.username))
@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
