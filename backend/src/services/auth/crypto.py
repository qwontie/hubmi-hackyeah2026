import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from utils.env import env

ALGORITHM = "HS256"
MAX_PASSWORD_BYTES = 72


def _encode(password: str) -> bytes:
    return password.encode()[:MAX_PASSWORD_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_encode(password), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(_encode(password), password_hash.encode())
    except ValueError:
        return False


def _secret() -> str:
    secret = env.auth.secret.get_secret_value()
    if not secret:
        message = "AUTH__SECRET is not set"
        raise RuntimeError(message)
    return secret


def create_session(admin_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(admin_id),
        "iat": now,
        "exp": now + timedelta(days=env.auth.session_days),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def session_admin_id(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
        return uuid.UUID(str(payload.get("sub", "")))
    except (jwt.PyJWTError, ValueError):
        return None
