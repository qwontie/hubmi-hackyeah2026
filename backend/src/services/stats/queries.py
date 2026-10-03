from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import TextClause, text
from sqlmodel.ext.asyncio.session import AsyncSession

from .schemas import (
    AiDay,
    AiKind,
    AiSpend,
    Bucket,
    ClusterTrend,
    FeedbackStats,
    InnovationFeedback,
    InnovationUsage,
    Period,
    Range,
    SeriesPoint,
    Stats,
    Totals,
)

TIMEZONE = "Europe/Warsaw"
LIST_LIMIT = 10
MIN_GROWTH_COUNT = 2
UNKNOWN_LABEL = "Nie podano"

TOTALS_SQL = text("""
SELECT
    count(*) FILTER (WHERE created_at >= :start) AS needs,
    count(*) FILTER (WHERE created_at < :start) AS needs_previous,
    count(*) FILTER (WHERE created_at >= :start AND nothing_fits) AS nothing_fits,
    count(*) FILTER (WHERE created_at >= :start AND status = 'new') AS waiting,
    count(*) FILTER (WHERE created_at >= :start AND status = 'answered') AS answered,
    count(*) FILTER (WHERE created_at >= :start AND status = 'closed') AS closed,
    count(*) FILTER (WHERE created_at >= :start AND contact_email IS NOT NULL)
        AS with_contact
FROM need
WHERE created_at >= :previous_start AND created_at < :end
""")

MESSAGES_SQL = text("""
SELECT
    count(*) FILTER (WHERE direction = 'from_author') AS author_messages,
    count(*) FILTER (WHERE direction = 'to_author') AS replies
FROM message
WHERE sent_at >= :start AND sent_at < :end
""")

FIRST_REPLY_SQL = text("""
SELECT percentile_cont(0.5) WITHIN GROUP (
    ORDER BY extract(epoch FROM first_reply.sent_at - n.created_at)
) / 3600 AS hours
FROM need n
JOIN LATERAL (
    SELECT min(m.sent_at) AS sent_at
    FROM message m
    WHERE m.need_id = n.id AND m.direction = 'to_author'
) first_reply ON first_reply.sent_at IS NOT NULL
WHERE n.created_at >= :start AND n.created_at < :end
""")

SERIES_SQL = text("""
WITH buckets AS (
    SELECT generate_series(
        date_trunc(:unit, CAST(:first_day AS timestamp)),
        CAST(:last_day AS timestamp),
        :step
    )::date AS start
)
SELECT
    buckets.start,
    count(n.id) AS needs,
    count(n.id) FILTER (WHERE n.nothing_fits) AS nothing_fits
FROM buckets
LEFT JOIN need n
    ON date_trunc(:unit, n.created_at AT TIME ZONE :tz)::date = buckets.start
    AND n.created_at >= :start AND n.created_at < :end
GROUP BY buckets.start
ORDER BY buckets.start
""")

BY_CATEGORY_SQL = text("""
SELECT n.category_slug AS slug, c.name AS name, count(*) AS count
FROM need n
LEFT JOIN category c ON c.slug = n.category_slug
WHERE n.created_at >= :start AND n.created_at < :end
GROUP BY n.category_slug, c.name
ORDER BY count DESC, c.name
""")

BY_POWIAT_SQL = text("""
SELECT powiat AS slug, count(*) AS count
FROM need
WHERE created_at >= :start AND created_at < :end
GROUP BY powiat
ORDER BY count DESC
""")

CLUSTERS_SQL = text("""
SELECT
    c.id,
    c.title,
    c.size,
    count(n.id) FILTER (WHERE n.created_at >= :start) AS current,
    count(n.id) FILTER (WHERE n.created_at < :start) AS previous
FROM need_cluster c
JOIN need n ON n.cluster_id = c.id
WHERE n.created_at >= :previous_start AND n.created_at < :end
GROUP BY c.id, c.title, c.size
""")

INNOVATIONS_SQL = text("""
SELECT
    i.slug,
    i.title,
    count(*) AS matches,
    count(*) FILTER (WHERE r.rank = 1) AS top_matches,
    avg(r.score) AS avg_score
FROM match_result r
JOIN innovation i ON i.id = r.innovation_id
WHERE r.created_at >= :start AND r.created_at < :end
GROUP BY i.slug, i.title
ORDER BY matches DESC, top_matches DESC
LIMIT :limit
""")

AI_KINDS_SQL = text("""
SELECT
    kind,
    count(*) AS calls,
    count(*) FILTER (WHERE NOT ok) AS failed,
    coalesce(sum(input_tokens), 0) AS input_tokens,
    coalesce(sum(output_tokens), 0) AS output_tokens,
    coalesce(sum(cost_usd), 0) AS cost_usd,
    avg(latency_ms) AS avg_latency_ms
FROM ai_call
WHERE created_at >= :start AND created_at < :end
GROUP BY kind
ORDER BY cost_usd DESC
""")

AI_DAYS_SQL = text("""
WITH days AS (
    SELECT generate_series(
        CAST(:first_day AS timestamp), CAST(:last_day AS timestamp), interval '1 day'
    )::date AS start
)
SELECT days.start, count(a.id) AS calls, coalesce(sum(a.cost_usd), 0) AS cost_usd
FROM days
LEFT JOIN ai_call a
    ON (a.created_at AT TIME ZONE :tz)::date = days.start
    AND a.created_at >= :start AND a.created_at < :end
GROUP BY days.start
ORDER BY days.start
""")


FEEDBACK_SQL = text("""
SELECT
    count(*) FILTER (WHERE kind = 'fits') AS fits,
    count(*) FILTER (WHERE kind = 'does_not_fit') AS does_not_fit,
    count(*) FILTER (WHERE kind = 'improvement') AS improvements
FROM feedback
WHERE created_at >= :start AND created_at < :end
""")

SIGNUPS_SQL = text("""
SELECT count(*) AS test_signups
FROM test_signup
WHERE created_at >= :start AND created_at < :end
""")

REJECTED_SQL = text("""
SELECT
    i.slug,
    i.title,
    count(*) FILTER (WHERE f.kind = 'fits') AS fits,
    count(*) FILTER (WHERE f.kind = 'does_not_fit') AS does_not_fit
FROM feedback f
JOIN innovation i ON i.id = f.innovation_id
WHERE f.created_at >= :start AND f.created_at < :end
GROUP BY i.slug, i.title
HAVING count(*) FILTER (WHERE f.kind = 'does_not_fit') > 0
ORDER BY does_not_fit DESC, fits ASC, i.title
LIMIT :limit
""")


def period_range(period: Period, now: datetime | None = None) -> Range:
    zone = ZoneInfo(TIMEZONE)
    local_now = (now or datetime.now(UTC)).astimezone(zone)
    first_day = local_now.date() - timedelta(days=period.days - 1)
    start = datetime.combine(first_day, time.min, tzinfo=zone)
    previous_start = datetime.combine(
        first_day - timedelta(days=period.days), time.min, tzinfo=zone
    )
    return Range(
        period=period,
        start=start.astimezone(UTC),
        end=local_now.astimezone(UTC),
        previous_start=previous_start.astimezone(UTC),
        timezone=TIMEZONE,
    )


async def rows(
    session: AsyncSession, statement: TextClause, params: dict[str, Any]
) -> list[Any]:
    connection = await session.connection()
    result = await connection.execute(statement, params)
    return list(result.mappings().all())


async def series(
    session: AsyncSession, bounds: dict[str, Any], *, unit: str, step: timedelta
) -> list[SeriesPoint]:
    found = await rows(session, SERIES_SQL, {**bounds, "unit": unit, "step": step})
    return [SeriesPoint.model_validate(row) for row in found]


def cluster_trends(found: list[Any]) -> tuple[list[ClusterTrend], list[ClusterTrend]]:
    trends = [
        ClusterTrend(
            id=row["id"],
            title=row["title"],
            size=row["size"],
            current=row["current"],
            previous=row["previous"],
            growth=row["current"] - row["previous"],
        )
        for row in found
    ]
    top = sorted(
        (trend for trend in trends if trend.current),
        key=lambda trend: (-trend.current, -trend.size, trend.title),
    )
    growing = sorted(
        (
            trend
            for trend in trends
            if trend.current >= MIN_GROWTH_COUNT and trend.growth > 0
        ),
        key=lambda trend: (-trend.growth, -trend.current, trend.title),
    )
    return top[:LIST_LIMIT], growing[:LIST_LIMIT]


async def ai_spend(session: AsyncSession, bounds: dict[str, Any]) -> AiSpend:
    kinds = [
        AiKind.model_validate(row) for row in await rows(session, AI_KINDS_SQL, bounds)
    ]
    days = [
        AiDay(start=row["start"], calls=row["calls"], cost_usd=float(row["cost_usd"]))
        for row in await rows(session, AI_DAYS_SQL, bounds)
    ]
    return AiSpend(
        calls=sum(kind.calls for kind in kinds),
        failed=sum(kind.failed for kind in kinds),
        cost_usd=round(sum(kind.cost_usd for kind in kinds), 6),
        by_kind=kinds,
        per_day=days,
    )


async def feedback_stats(
    session: AsyncSession, bounds: dict[str, Any]
) -> FeedbackStats:
    votes = (await rows(session, FEEDBACK_SQL, bounds))[0]
    signups = (await rows(session, SIGNUPS_SQL, bounds))[0]["test_signups"]
    rejected = await rows(session, REJECTED_SQL, {**bounds, "limit": LIST_LIMIT})
    cast = votes["fits"] + votes["does_not_fit"]
    return FeedbackStats(
        fits=votes["fits"],
        does_not_fit=votes["does_not_fit"],
        fit_share=round(votes["fits"] / cast, 4) if cast else None,
        improvements=votes["improvements"],
        test_signups=signups,
        most_rejected=[InnovationFeedback.model_validate(row) for row in rejected],
    )


async def collect(
    session: AsyncSession, period: Period, powiat_names: dict[str, str]
) -> Stats:
    span = period_range(period)
    local_end = span.end.astimezone(ZoneInfo(TIMEZONE)).date()
    local_start = span.start.astimezone(ZoneInfo(TIMEZONE)).date()
    bounds: dict[str, Any] = {
        "start": span.start,
        "end": span.end,
        "previous_start": span.previous_start,
        "tz": TIMEZONE,
        "first_day": datetime.combine(local_start, time.min),
        "last_day": datetime.combine(local_end, time.min),
    }
    totals_row = (await rows(session, TOTALS_SQL, bounds))[0]
    messages_row = (await rows(session, MESSAGES_SQL, bounds))[0]
    first_reply = (await rows(session, FIRST_REPLY_SQL, bounds))[0]["hours"]
    needs = totals_row["needs"]
    totals = Totals(
        **totals_row,
        **messages_row,
        nothing_fits_share=round(totals_row["nothing_fits"] / needs, 4)
        if needs
        else 0.0,
        median_first_reply_hours=None if first_reply is None else round(first_reply, 2),
    )
    by_category = [
        Bucket(slug=row["slug"], name=row["name"] or UNKNOWN_LABEL, count=row["count"])
        for row in await rows(session, BY_CATEGORY_SQL, bounds)
    ]
    by_powiat = [
        Bucket(
            slug=row["slug"],
            name=powiat_names.get(row["slug"] or "", row["slug"] or UNKNOWN_LABEL),
            count=row["count"],
        )
        for row in await rows(session, BY_POWIAT_SQL, bounds)
    ]
    top, growing = cluster_trends(await rows(session, CLUSTERS_SQL, bounds))
    innovations = [
        InnovationUsage.model_validate(row)
        for row in await rows(session, INNOVATIONS_SQL, {**bounds, "limit": LIST_LIMIT})
    ]
    return Stats(
        range=span,
        totals=totals,
        per_day=await series(session, bounds, unit="day", step=timedelta(days=1)),
        per_week=await series(session, bounds, unit="week", step=timedelta(weeks=1)),
        by_category=by_category,
        by_powiat=by_powiat,
        top_clusters=top,
        growing_clusters=growing,
        top_innovations=innovations,
        feedback=await feedback_stats(session, bounds),
        ai=await ai_spend(session, bounds),
    )
