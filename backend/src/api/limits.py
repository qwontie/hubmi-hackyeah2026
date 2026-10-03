import hashlib
import hmac
import math
import time
from collections import deque
from dataclasses import dataclass

from fastapi import Request, status
from sqlalchemy import text

from api.errors import STATUS_MESSAGES, ApiError
from utils.db import session_scope
from utils.env import env

SWEEP_EVERY = 1000
PER_MINUTE = 60
PER_DAY = 86400
COUNT_SQL = text(
    "INSERT INTO rate_counter (key_hash, window_start, hits) "
    "VALUES (:key_hash, now(), 1) "
    "ON CONFLICT (key_hash) DO UPDATE SET "
    "hits = CASE WHEN rate_counter.window_start <= now() - "
    "make_interval(secs => :seconds) THEN 1 ELSE rate_counter.hits + 1 END, "
    "window_start = CASE WHEN rate_counter.window_start <= now() - "
    "make_interval(secs => :seconds) THEN now() ELSE rate_counter.window_start END "
    "RETURNING hits, ceil(extract(epoch FROM rate_counter.window_start + "
    "make_interval(secs => :seconds) - now()))::int AS retry"
)
SWEEP_SQL = text(
    "DELETE FROM rate_counter "
    "WHERE window_start < now() - make_interval(secs => :seconds)"
)


@dataclass(frozen=True, slots=True)
class Rule:
    count: int
    seconds: int


class RateLimiter:
    def __init__(self, name: str, *rules: Rule) -> None:
        self.name = name
        self.rules = rules
        self.window = max(rule.seconds for rule in rules)
        self.hits: dict[str, deque[float]] = {}
        self.calls = 0

    def check(self, key: str) -> None:
        now = time.monotonic()
        self.calls += 1
        if self.calls % SWEEP_EVERY == 0:
            self.sweep(now)
        hits = self.hits.setdefault(key, deque())
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        for rule in self.rules:
            recent = [stamp for stamp in hits if stamp > now - rule.seconds]
            if len(recent) >= rule.count:
                raise too_many(math.ceil(recent[-rule.count] + rule.seconds - now))
        hits.append(now)

    def sweep(self, now: float) -> None:
        stale = [
            key
            for key, hits in self.hits.items()
            if not hits or hits[-1] <= now - self.window
        ]
        for key in stale:
            del self.hits[key]

    async def __call__(self, request: Request) -> None:
        self.check(client_ip(request))


def too_many(retry: int) -> ApiError:
    return ApiError(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "rate_limited",
        STATUS_MESSAGES[429],
        headers={"Retry-After": str(max(1, retry))},
    )


def hashed_key(scope: str, value: str) -> str:
    secret = env.auth.secret.get_secret_value().encode()
    return hmac.new(secret, f"{scope}:{value}".encode(), hashlib.sha256).hexdigest()


class PersistentRateLimiter:
    def __init__(self, name: str, *rules: Rule) -> None:
        self.name = name
        self.rules = rules
        self.window = max(rule.seconds for rule in rules)
        self.calls = 0

    async def check(self, key: str) -> None:
        self.calls += 1
        retry = 0
        async with session_scope() as session:
            connection = await session.connection()
            if self.calls % SWEEP_EVERY == 0:
                await connection.execute(SWEEP_SQL, {"seconds": self.window})
            for rule in self.rules:
                row = (
                    await connection.execute(
                        COUNT_SQL,
                        {
                            "key_hash": hashed_key(f"{self.name}:{rule.seconds}", key),
                            "seconds": rule.seconds,
                        },
                    )
                ).one()
                if row.hits > rule.count:
                    retry = max(retry, int(row.retry))
            await session.commit()
        if retry:
            raise too_many(retry)

    async def __call__(self, request: Request) -> None:
        await self.check(client_ip(request))


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limit(
    name: str, *, per_minute: int | None = None, per_day: int | None = None
) -> RateLimiter:
    rules = [
        Rule(count, seconds)
        for count, seconds in ((per_minute, PER_MINUTE), (per_day, PER_DAY))
        if count
    ]
    if not rules:
        message = f"rate limit {name} has no rules"
        raise ValueError(message)
    return RateLimiter(name, *rules)


def persistent_rate_limit(
    name: str, *, per_minute: int | None = None, per_day: int | None = None
) -> PersistentRateLimiter:
    rules = [
        Rule(count, seconds)
        for count, seconds in ((per_minute, PER_MINUTE), (per_day, PER_DAY))
        if count
    ]
    if not rules:
        message = f"rate limit {name} has no rules"
        raise ValueError(message)
    return PersistentRateLimiter(name, *rules)
