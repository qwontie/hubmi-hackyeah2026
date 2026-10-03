import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlmodel import col

from utils.db import session_scope
from utils.db.models.ai_call import AiCall
from utils.logging import logger

PRICES_PER_MILLION: dict[str, tuple[float, float]] = {
    "gemini-embedding-001": (0.15, 0.0),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
}
DEFAULT_PRICE = (0.30, 2.50)
DAILY_BUDGET_USD = 5.0
BUDGET_CACHE_SECONDS = 30.0


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
    _spent_cache["at"] = 0.0
    return cost


_spent_cache: dict[str, float] = {"at": 0.0, "value": 0.0}


async def spent_last_day() -> float:
    now = time.monotonic()
    if now - _spent_cache["at"] < BUDGET_CACHE_SECONDS:
        return _spent_cache["value"]
    since = datetime.now(UTC) - timedelta(days=1)
    async with session_scope() as session:
        value = await session.scalar(
            select(func.coalesce(func.sum(AiCall.cost_usd), 0)).where(
                col(AiCall.created_at) >= since
            )
        )
    _spent_cache.update(at=now, value=float(value or 0))
    return _spent_cache["value"]


async def ensure_budget() -> None:
    if await spent_last_day() >= DAILY_BUDGET_USD:
        raise AiBudgetExceededError
