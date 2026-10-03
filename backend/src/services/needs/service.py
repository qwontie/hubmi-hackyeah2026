import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import text as sql
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.ai import (
    AiBudgetExceededError,
    AiUnavailableError,
    embed_query,
    embed_titles,
)
from services.bus import bus
from services.search import (
    Hit,
    Reasoned,
    apply_decision,
    cached_query_embedding,
    category_for,
    decide,
    fallback,
    fallback_reason,
    hybrid_search,
    letters_ratio,
    peek_query_embedding,
    word_count,
)
from utils.db.models.innovation import Innovation, InnovationStatus
from utils.db.models.match_result import MatchResult
from utils.db.models.need import Need, NeedCluster, NeedOrigin

from .clusters import assign_cluster, nearest_cluster, schedule_summary, similar_count
from .enrich import schedule_enrichment
from .intake import (
    MAX_TEXT,
    TextRejectedError,
    collapse,
    dedupe_key,
    first_words,
    intake_text,
)
from .payloads import need_payload
from .tokens import new_token, token_matches

MIN_SEARCH_TEXT = 5
MIN_LETTERS = 0.6
CANDIDATES = 12
DUPLICATE_WINDOW = timedelta(hours=24)
type SearchReason = Literal["unclear", "no_match"]
UNCLEAR: SearchReason = "unclear"
NO_MATCH: SearchReason = "no_match"
UNCLEAR_TEXT = "unclear_text"
UNCLEAR_MESSAGE = (
    "Nie rozumiemy opisu. Napisz w kilku słowach, z jakim problemem się mierzysz."
)


class NeedNotFoundError(LookupError):
    pass


def search_text(text: str) -> str | None:
    text = collapse(text)[:MAX_TEXT]
    if (
        len(text) < MIN_SEARCH_TEXT
        or letters_ratio(text) < MIN_LETTERS
        or word_count(text) < 1
    ):
        return None
    return text


@dataclass(slots=True)
class MatchOutcome:
    need: Need
    token: str
    results: list[Reasoned]
    similar_count: int
    cluster: NeedCluster | None
    degraded: bool


@dataclass(slots=True)
class SearchOutcome:
    results: list[Reasoned]
    similar_count: int
    cluster: NeedCluster | None
    degraded: bool
    reason: SearchReason | None


@dataclass(slots=True)
class FormOutcome:
    need: Need
    token: str
    similar_count: int
    cluster: NeedCluster | None
    duplicate: bool = False


def match_refs(results: list[Reasoned]) -> list[dict[str, Any]]:
    return [
        {
            "slug": r.hit.innovation.slug,
            "title": r.hit.innovation.title,
            "score": r.hit.score,
        }
        for r in results
    ]


async def stored_match_refs(
    session: AsyncSession, need_id: uuid.UUID, limit: int = 3
) -> list[dict[str, Any]]:
    rows = (
        await session.exec(
            select(Innovation.slug, Innovation.title, MatchResult.score)
            .join(MatchResult, col(MatchResult.innovation_id) == Innovation.id)
            .where(col(MatchResult.need_id) == need_id)
            .order_by(col(MatchResult.rank))
            .limit(limit)
        )
    ).all()
    return [
        {"slug": slug, "title": title, "score": score} for slug, title, score in rows
    ]


def _publish_created(
    need: Need, cluster: NeedCluster | None, matches: list[dict[str, Any]]
) -> None:
    bus.publish("need.created", need_payload(need, cluster, matches))
    if cluster is not None and cluster.summary_stale:
        schedule_summary(cluster.id)


async def match_need(
    session: AsyncSession,
    text: str,
    *,
    powiat: str | None,
    vector: list[float] | None = None,
) -> MatchOutcome:
    cleaned = search_text(text)
    if cleaned is None:
        raise TextRejectedError(UNCLEAR_TEXT, UNCLEAR_MESSAGE)
    text = cleaned
    vector = vector or await embed_query(text, kind="embed_need")
    hits = await hybrid_search(session, text, vector, limit=CANDIDATES)
    try:
        decision = await decide(text, hits) if hits else None
    except (AiUnavailableError, AiBudgetExceededError):
        decision = None
        degraded = True
    else:
        degraded = False
    if decision is not None and not decision.is_problem:
        raise TextRejectedError(UNCLEAR_TEXT, UNCLEAR_MESSAGE)
    results = apply_decision(decision, hits) if decision else fallback(hits)
    title = (decision.title.strip() if decision else "") or first_words(text)
    similar = await similar_count(session, vector)
    token, token_hash = new_token()
    need = Need(
        text=text,
        title=title,
        origin=NeedOrigin.MATCH,
        powiat=powiat,
        category_slug=await category_for(session, vector),
        edit_token_hash=token_hash,
        embedding=vector,
    )
    session.add(need)
    await session.flush()
    title_vector = (await embed_titles([title], kind="embed_need_title"))[0]
    cluster = await assign_cluster(
        session, need, title=title, title_vector=title_vector
    )
    for rank, result in enumerate(results, start=1):
        session.add(
            MatchResult(
                need_id=need.id,
                innovation_id=result.hit.innovation.id,
                rank=rank,
                score=result.hit.score,
                reason=result.reason,
            )
        )
    await session.commit()
    await session.refresh(need)
    await session.refresh(cluster)
    _publish_created(need, cluster, match_refs(results))
    return MatchOutcome(
        need=need,
        token=token,
        results=results,
        similar_count=similar,
        cluster=cluster,
        degraded=degraded,
    )


async def search_need(session: AsyncSession, text: str) -> SearchOutcome:
    cleaned = search_text(text)
    if cleaned is None:
        return SearchOutcome([], 0, None, degraded=False, reason=UNCLEAR)
    degraded = False
    vector: list[float] | None
    try:
        vector = await cached_query_embedding(cleaned, kind="embed_need")
    except (AiUnavailableError, AiBudgetExceededError):
        vector = None
        degraded = True
    hits = await hybrid_search(session, cleaned, vector, limit=CANDIDATES)
    try:
        decision = await decide(cleaned, hits) if hits else None
    except (AiUnavailableError, AiBudgetExceededError):
        decision = None
        degraded = True
    if decision is not None and not decision.is_problem:
        return SearchOutcome([], 0, None, degraded=degraded, reason=UNCLEAR)
    results = apply_decision(decision, hits) if decision else fallback(hits)
    return SearchOutcome(
        results=results,
        similar_count=await similar_count(session, vector) if vector else 0,
        cluster=await nearest_cluster(session, vector) if vector else None,
        degraded=degraded,
        reason=None if results else NO_MATCH,
    )


async def _recent_duplicate(session: AsyncSession, key: str) -> Need | None:
    await session.scalar(
        sql("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key}
    )
    return (
        await session.exec(
            select(Need)
            .where(
                col(Need.dedupe_key) == key,
                col(Need.created_at) >= datetime.now(UTC) - DUPLICATE_WINDOW,
            )
            .order_by(col(Need.created_at).desc())
            .limit(1)
        )
    ).first()


def _set_contact(need: Need, contact_email: str | None) -> None:
    if contact_email is None:
        return
    need.contact_email = contact_email
    need.contact_consent = True
    need.consent_at = datetime.now(UTC)


async def _reissue(
    session: AsyncSession, need: Need, contact_email: str | None
) -> FormOutcome:
    token, token_hash = new_token()
    need.edit_token_hash = token_hash
    _set_contact(need, contact_email)
    session.add(need)
    await session.commit()
    await session.refresh(need)
    cluster = (
        await session.get(NeedCluster, need.cluster_id) if need.cluster_id else None
    )
    similar = (
        await similar_count(session, list(need.embedding), exclude=need.id)
        if need.embedding is not None
        else 0
    )
    return FormOutcome(
        need=need, token=token, similar_count=similar, cluster=cluster, duplicate=True
    )


async def _store_shown(
    session: AsyncSession, need: Need, shown: list[str], hits: list[Hit]
) -> None:
    if not shown:
        return
    found = {
        innovation.slug: innovation
        for innovation in (
            await session.exec(
                select(Innovation).where(
                    col(Innovation.slug).in_(shown),
                    col(Innovation.status) == InnovationStatus.PUBLISHED,
                )
            )
        ).all()
    }
    scores = {hit.innovation.slug: hit.score for hit in hits}
    rank = 0
    for slug in shown:
        innovation = found.get(slug)
        if innovation is None:
            continue
        rank += 1
        session.add(
            MatchResult(
                need_id=need.id,
                innovation_id=innovation.id,
                rank=rank,
                score=scores.get(slug, 0.0),
                reason=fallback_reason(innovation),
            )
        )


async def create_need(  # noqa: PLR0913
    session: AsyncSession,
    text: str,
    *,
    powiat: str | None,
    contact_email: str | None,
    shown_innovation_slugs: list[str] | None = None,
    vector: list[float] | None = None,
    client: str | None = None,
    honeypot: str | None = None,
) -> FormOutcome:
    text = intake_text(text, honeypot=honeypot)
    key = dedupe_key(client, text) if client else None
    if key is not None:
        existing = await _recent_duplicate(session, key)
        if existing is not None:
            return await _reissue(session, existing, contact_email)
    vector = vector or peek_query_embedding(text)
    shown = shown_innovation_slugs or []
    token, token_hash = new_token()
    need = Need(
        text=text,
        title=first_words(text),
        origin=NeedOrigin.FORM,
        powiat=powiat,
        nothing_fits=bool(shown),
        edit_token_hash=token_hash,
        embedding=vector,
        dedupe_key=key,
    )
    _set_contact(need, contact_email)
    session.add(need)
    await session.flush()
    hits: list[Hit] = []
    similar = 0
    if vector is not None:
        hits = await hybrid_search(session, text, vector, limit=CANDIDATES)
        need.category_slug = await category_for(session, vector)
        similar = await similar_count(session, vector, exclude=need.id)
    await _store_shown(session, need, shown, hits)
    await session.commit()
    await session.refresh(need)
    _publish_created(need, None, await stored_match_refs(session, need.id))
    schedule_enrichment(need.id)
    return FormOutcome(need=need, token=token, similar_count=similar, cluster=None)


async def update_need(  # noqa: PLR0913
    session: AsyncSession,
    need_id: uuid.UUID,
    token: str | None,
    *,
    powiat: str | None = None,
    contact_email: str | None = None,
    contact_email_provided: bool = False,
    contact_consent: bool | None = None,
    nothing_fits: bool | None = None,
) -> Need:
    need = await session.get(Need, need_id)
    if need is None or not token_matches(token, need.edit_token_hash):
        raise NeedNotFoundError
    if powiat is not None:
        need.powiat = powiat
    if (contact_email_provided and contact_email is None) or contact_consent is False:
        need.contact_email = None
        need.contact_consent = False
        need.consent_at = None
    elif contact_email is not None:
        _set_contact(need, contact_email)
    if nothing_fits is not None:
        need.nothing_fits = nothing_fits
    session.add(need)
    await session.commit()
    await session.refresh(need)
    cluster = (
        await session.get(NeedCluster, need.cluster_id) if need.cluster_id else None
    )
    bus.publish("need.updated", need_payload(need, cluster, []))
    return need
