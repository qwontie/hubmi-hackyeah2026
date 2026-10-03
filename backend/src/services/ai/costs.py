import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlmodel import col

from utils.db import session_scope
from utils.db.models.ai_call import AiCall
from utils.env import env
from utils.logging import logger

PRICES_PER_MILLION: dict[str, tuple[float, float]] = {
    "gemini-embedding-001": (0.15, 0.0),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-3.1-flash-image": (0.50, 60.0),
    "gemini-3.1-flash-lite-image": (0.25, 30.0),
}
DEFAULT_PRICE = (0.30, 2.50)
BUDGET_CACHE_SECONDS = 30.0
BATCH_MODE_ENV = "AI_BATCH_MODE"
_scope_override: ContextVar[str | None] = ContextVar("ai_scope", default=None)


class AiBudgetExceededError(RuntimeError):
    pass


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = PRICES_PER_MILLION.get(model, DEFAULT_PRICE)
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


async def log_ai_call(  # noqa: PLR0913
    *,
    kind: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    ok: bool,
    error: str | None = None,
) -> float:
    cost = cost_usd(model, input_tokens, output_tokens)
    scope = current_scope()
    logger.info(
        "ai %s %s in=%d out=%d cost=$%.6f %dms ok=%s",
        kind,
        model,
        input_tokens,
        output_tokens,
        cost,
        latency_ms,
        ok,
    )
    try:
        async with session_scope() as session:
            session.add(
                AiCall(
                    kind=kind,
                    scope=scope,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    ok=ok,
                    error=error[:500] if error else None,
                )
            )
            await session.commit()
    except Exception:
        logger.exception("failed to store ai_call")
    _spent_cache[scope]["at"] = 0.0
    return cost


_spent_cache: dict[str, dict[str, float]] = {
    "public": {"at": 0.0, "value": 0.0},
    "batch": {"at": 0.0, "value": 0.0},
}


def current_scope() -> str:
    return _scope_override.get() or (
        "batch" if os.getenv(BATCH_MODE_ENV) == "1" else "public"
    )


@contextmanager
def use_budget_scope(scope: str) -> Iterator[None]:
    token = _scope_override.set(scope)
    try:
        yield
    finally:
        _scope_override.reset(token)


def budget_limit() -> float:
    if current_scope() == "batch":
        return env.llm.batch_daily_budget_usd
    return env.llm.daily_budget_usd


async def spent_last_day() -> float:
    scope = current_scope()
    cache = _spent_cache[scope]
    now = time.monotonic()
    if now - cache["at"] < BUDGET_CACHE_SECONDS:
        return cache["value"]
    since = datetime.now(UTC) - timedelta(days=1)
    async with session_scope() as session:
        value = await session.scalar(
            select(func.coalesce(func.sum(AiCall.cost_usd), 0)).where(
                col(AiCall.created_at) >= since, col(AiCall.scope) == scope
            )
        )
    cache.update(at=now, value=float(value or 0))
    return cache["value"]


async def ensure_budget() -> None:
    if await spent_last_day() >= budget_limit():
        raise AiBudgetExceededError
