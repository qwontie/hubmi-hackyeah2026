import random
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")
SPAN_DAYS = 42
RISING_SHAPE = 2.2
FLAT_SHAPE = 1.0
FIRST_HOUR = 7
LAST_HOUR = 22
MARGIN = timedelta(hours=1)
OFFICE_START = 8
OFFICE_END = 16
SATURDAY = 5


def _rng(seed: str) -> random.Random:
    return random.Random(seed)  # noqa: S311


def _local_hour(moment: datetime, rng: random.Random) -> datetime:
    local = moment.astimezone(WARSAW)
    hour = rng.randint(FIRST_HOUR, LAST_HOUR - 1)
    local = local.replace(
        hour=hour, minute=rng.randint(0, 59), second=rng.randint(0, 59)
    )
    return local.astimezone(UTC)


def topic_ages(keys: list[str], *, rising: bool) -> dict[str, float]:
    shape = RISING_SHAPE if rising else FLAT_SHAPE
    ordered = sorted(keys, key=lambda key: _rng(f"order:{key}").random())
    return {
        key: SPAN_DAYS * ((index + _rng(f"age:{key}").random()) / len(ordered)) ** shape
        for index, key in enumerate(ordered)
    }


def need_time(key: str, days: float, *, thread_hours: float, now: datetime) -> datetime:
    rng = _rng(f"need:{key}")
    moment = _local_hour(now - timedelta(days=days), rng)
    latest = now - timedelta(hours=thread_hours) - MARGIN
    if moment > latest:
        moment = latest - timedelta(minutes=rng.randint(0, 600))
    return moment


def days_ago(key: str, days: float, *, now: datetime) -> datetime:
    rng = _rng(f"item:{key}")
    moment = _local_hour(now - timedelta(days=days), rng)
    return min(moment, now - MARGIN)


def spread(key: str, count: int, *, now: datetime) -> list[datetime]:
    rng = _rng(f"spread:{key}")
    moments = [
        _local_hour(now - timedelta(days=SPAN_DAYS * rng.random() ** FLAT_SHAPE), rng)
        for _ in range(count)
    ]
    return sorted(min(m, now - MARGIN) for m in moments)


def after(moment: datetime, hours: float, *, now: datetime) -> datetime:
    return min(moment + timedelta(hours=hours), now - timedelta(minutes=5))


def office(moment: datetime, key: str, *, now: datetime) -> datetime:
    rng = _rng(f"office:{key}")
    local = moment.astimezone(WARSAW)
    while local.weekday() >= SATURDAY or local.hour >= OFFICE_END:
        local = (local + timedelta(days=1)).replace(
            hour=OFFICE_START, minute=rng.randint(0, 59)
        )
    if local.hour < OFFICE_START:
        local = local.replace(hour=OFFICE_START, minute=rng.randint(0, 59))
    return min(local.astimezone(UTC), now - timedelta(minutes=5))
