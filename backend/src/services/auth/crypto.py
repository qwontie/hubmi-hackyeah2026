import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

import bcrypt
import jwt

from utils.env import env

ALGORITHM = "HS256"
MAX_PASSWORD_BYTES = 72
BCRYPT_WORKERS = 4
_bcrypt_pool = ThreadPoolExecutor(
    max_workers=BCRYPT_WORKERS, thread_name_prefix="hubmi-bcrypt"
)


class SessionClaims(NamedTuple):
    admin_id: uuid.UUID
    token_version: int


def _encode(password: str) -> bytes:
    return password.encode()[:MAX_PASSWORD_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_encode(password), bcrypt.gensalt()).decode()


async def hash_password_async(password: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_bcrypt_pool, hash_password, password)


def _verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(_encode(password), password_hash.encode())
    except ValueError:
        return False


async def verify_password(password: str, password_hash: str) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _bcrypt_pool, _verify_password, password, password_hash
    )


def _secret() -> str:
    secret = env.auth.secret.get_secret_value()
    if not secret:
        message = "AUTH__SECRET is not set"
        raise RuntimeError(message)
    return secret


def create_session(admin_id: uuid.UUID, token_version: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(admin_id),
        "ver": token_version,
        "iat": now,
        "exp": now + timedelta(hours=env.auth.session_hours),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def session_claims(token: str) -> SessionClaims | None:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
        return SessionClaims(
            uuid.UUID(str(payload.get("sub", ""))), int(payload.get("ver", -1))
        )
    except (jwt.PyJWTError, TypeError, ValueError):
        return None
