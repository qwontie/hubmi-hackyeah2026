import hashlib
import hmac
import math
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from api.limits import client_ip
from utils.env import env

RESET_SECONDS = 900
BACKOFF_SECONDS = 30
MAX_BACKOFF_SECONDS = 900
BLOCK_AFTER_FAILURES = 5
ACCOUNT_BLOCK_AFTER_FAILURES = 20
ACCOUNT_MAX_BACKOFF_SECONDS = 60


class LoginBlockedError(RuntimeError):
    def __init__(self, retry_after: int) -> None:
        super().__init__("login blocked")
        self.retry_after = retry_after


def _key(scope: str, value: str) -> str:
    secret = env.auth.secret.get_secret_value().encode()
    return hmac.new(secret, f"{scope}:{value}".encode(), hashlib.sha256).hexdigest()


class LoginGuard:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _keys(self, request: Request, login: str) -> tuple[str, str]:
        return (_key("ip", client_ip(request)), _key("account", login.strip().lower()))

    async def check(self, request: Request, login: str) -> None:
        connection = await self.session.connection()
        rows = await connection.execute(
            text(
                "SELECT blocked_until FROM auth_login_guard "
                "WHERE key_hash IN (:ip_key, :account_key) "
                "AND blocked_until > now() ORDER BY blocked_until DESC LIMIT 1"
            ),
            dict(
                zip(("ip_key", "account_key"), self._keys(request, login), strict=True)
            ),
        )
        blocked_until = rows.scalar_one_or_none()
        if blocked_until is not None:
            retry = max(
                1, math.ceil((blocked_until - datetime.now(UTC)).total_seconds())
            )
            raise LoginBlockedError(retry)

    async def failed(self, request: Request, login: str) -> None:
        statement = text(
            "INSERT INTO auth_login_guard "
            "(key_hash, failures, blocked_until, updated_at) "
            "VALUES (:key_hash, 1, NULL, now()) "
            "ON CONFLICT (key_hash) DO UPDATE SET "
            "failures = CASE WHEN auth_login_guard.updated_at < now() - "
            "make_interval(secs => :reset_seconds) THEN 1 "
            "ELSE auth_login_guard.failures + 1 END, "
            "blocked_until = CASE WHEN "
            "(CASE WHEN auth_login_guard.updated_at < now() - "
            "make_interval(secs => :reset_seconds) THEN 1 "
            "ELSE auth_login_guard.failures + 1 END) >= :block_after THEN "
            "now() + make_interval(secs => LEAST(:max_backoff, :backoff * "
            "power(2, (CASE WHEN auth_login_guard.updated_at < now() - "
            "make_interval(secs => :reset_seconds) THEN 1 "
            "ELSE auth_login_guard.failures + 1 END) - :block_after)::int)) "
            "ELSE NULL END, updated_at = now()"
        )
        connection = await self.session.connection()
        keys = zip(
            self._keys(request, login),
            (
                (BLOCK_AFTER_FAILURES, MAX_BACKOFF_SECONDS),
                (ACCOUNT_BLOCK_AFTER_FAILURES, ACCOUNT_MAX_BACKOFF_SECONDS),
            ),
            strict=True,
        )
        for key_hash, (block_after, max_backoff) in keys:
            await connection.execute(
                statement,
                {
                    "key_hash": key_hash,
                    "reset_seconds": RESET_SECONDS,
                    "block_after": block_after,
                    "backoff": BACKOFF_SECONDS,
                    "max_backoff": max_backoff,
                },
            )
        await self.session.commit()

    async def succeeded(self, request: Request, login: str) -> None:
        ip_key, account_key = self._keys(request, login)
        connection = await self.session.connection()
        await connection.execute(
            text(
                "DELETE FROM auth_login_guard WHERE key_hash IN (:ip_key, :account_key)"
            ),
            {"ip_key": ip_key, "account_key": account_key},
        )
        await self.session.commit()
