import math
import time
from collections import deque
from dataclasses import dataclass

from fastapi import Request, status

from api.errors import STATUS_MESSAGES, ApiError

SWEEP_EVERY = 1000
PER_MINUTE = 60
PER_DAY = 86400


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
                retry = max(1, math.ceil(recent[-rule.count] + rule.seconds - now))
                raise ApiError(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    "rate_limited",
                    STATUS_MESSAGES[429],
                    headers={"Retry-After": str(retry)},
                )
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


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("cf-connecting-ip")
    if forwarded:
        return forwarded.strip()
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
