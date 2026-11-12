"""Mots de passe (bcrypt) et jetons d'accès (JWT)."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    # bcrypt ajoute automatiquement un "sel" aléatoire : deux utilisateurs
    # avec le même mot de passe ont des hash différents.
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


# Hash factice : sert à faire le même travail quand l'utilisateur n'existe pas,
# pour qu'un attaquant ne puisse pas deviner les noms valides via le temps de réponse.
DUMMY_HASH = hash_password("mot-de-passe-factice")


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": username, "exp": expire}, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    # Lève jwt.PyJWTError si la signature est fausse ou si le jeton a expiré.
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
