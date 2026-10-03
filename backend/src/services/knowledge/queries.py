import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Float, func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.search import nearest_innovations
from services.search.vector import cosine_distance
from utils.db.models.category import Category
from utils.db.models.challenge import Challenge
from utils.db.models.material import KnowledgeStatus, Material

from .materials import related_materials
from .schemas import (
    ChallengeDetail,
    ChallengeSummary,
    MaterialDetail,
    MaterialSummary,
    RelatedChallenge,
    RelatedInnovation,
    RelatedMaterial,
)

RELATED_INNOVATIONS = 5
RELATED_MATERIALS = 3
RELATED_CHALLENGES = 3
MIN_RELATED_SCORE = 0.55


@dataclass(frozen=True, slots=True)
class ChallengeFilters:
    area: str | None = None
    q: str | None = None
    status: KnowledgeStatus | None = KnowledgeStatus.PUBLISHED
    verified: bool | None = None


def _ts_query(q: str):  # noqa: ANN202
    return func.websearch_to_tsquery("simple", func.hubmi_unaccent(q))


async def list_challenges(
    session: AsyncSession, filters: ChallengeFilters, *, page: int, per_page: int
) -> tuple[list[Challenge], int]:
    conditions: list = []
    if filters.status is not None:
        conditions.append(Challenge.status == filters.status)
    if filters.area:
        conditions.append(Challenge.area == filters.area)
    if filters.verified is True:
        conditions.append(col(Challenge.verified_at).is_not(None))
    if filters.verified is False:
        conditions.append(col(Challenge.verified_at).is_(None))
    statement = select(Challenge).where(*conditions)
    count_statement = select(func.count()).select_from(Challenge).where(*conditions)
    if filters.q:
        query = _ts_query(filters.q)
        matches = col(Challenge.search).op("@@")(query)
        statement = statement.where(matches).order_by(
            func.ts_rank_cd(col(Challenge.search), query).desc()
        )
        count_statement = count_statement.where(matches)
    else:
        statement = statement.order_by(col(Challenge.position), col(Challenge.title))
    total = int((await session.exec(count_statement)).one())
    rows = (
        await session.exec(statement.offset((page - 1) * per_page).limit(per_page))
    ).all()
    return list(rows), total


async def area_counts(session: AsyncSession) -> dict[str, int]:
    rows = (
        await session.exec(
            select(Challenge.area, func.count())
            .where(Challenge.status == KnowledgeStatus.PUBLISHED)
            .group_by(Challenge.area)
        )
    ).all()
    return {str(area): int(count) for area, count in rows}


async def kind_counts(session: AsyncSession) -> dict[str, int]:
    rows = (
        await session.exec(
            select(Material.kind, func.count())
            .where(Material.status == KnowledgeStatus.PUBLISHED)
            .group_by(Material.kind)
        )
    ).all()
    return {str(kind): int(count) for kind, count in rows}


async def find_challenge(
    session: AsyncSession, key: str, *, published_only: bool = True
) -> Challenge | None:
    try:
        challenge = await session.get(Challenge, uuid.UUID(key))
    except ValueError:
        challenge = (
            await session.exec(select(Challenge).where(Challenge.slug == key))
        ).first()
    if challenge is None:
        return None
    if published_only and challenge.status != KnowledgeStatus.PUBLISHED:
        return None
    return challenge


async def nearest_challenges(
    session: AsyncSession,
    vector: Sequence[float],
    *,
    limit: int = RELATED_CHALLENGES,
    exclude_ids: Sequence[uuid.UUID] = (),
    min_score: float = 0.0,
) -> list[tuple[Challenge, float]]:
    distance = cosine_distance(Challenge.embedding, list(vector))
    score = (1 - distance).cast(Float).label("score")
    statement = (
        select(Challenge, score)
        .where(
            Challenge.status == KnowledgeStatus.PUBLISHED,
            col(Challenge.embedding).is_not(None),
        )
        .order_by(distance)
        .limit(limit)
    )
    if exclude_ids:
        statement = statement.where(col(Challenge.id).not_in(list(exclude_ids)))
    rows = (await session.exec(statement)).all()
    return [(row[0], float(row[1])) for row in rows if float(row[1]) >= min_score]


async def _categories(session: AsyncSession) -> dict[str, Category]:
    return {c.slug: c for c in (await session.exec(select(Category))).all()}


async def _related_innovations(
    session: AsyncSession, vector: Sequence[float] | None
) -> list[RelatedInnovation]:
    if vector is None:
        return []
    hits = await nearest_innovations(session, list(vector), limit=RELATED_INNOVATIONS)
    categories = await _categories(session)
    return [
        RelatedInnovation.build(innovation, score, categories)
        for innovation, score in hits
        if score >= MIN_RELATED_SCORE
    ]


async def challenge_detail(
    session: AsyncSession, challenge: Challenge
) -> ChallengeDetail:
    vector = None if challenge.embedding is None else list(challenge.embedding)
    materials: list[RelatedMaterial] = []
    if vector is not None:
        hits = await related_materials(
            session, vector, limit=RELATED_MATERIALS, min_score=MIN_RELATED_SCORE
        )
        materials = [
            RelatedMaterial(**MaterialSummary.build(m).model_dump(), score=round(s, 4))
            for m, s in hits
        ]
    return ChallengeDetail(
        **ChallengeSummary.build(challenge).model_dump(),
        description=challenge.description,
        verified_at=challenge.verified_at,
        updated_at=challenge.updated_at,
        related_innovations=await _related_innovations(session, vector),
        related_materials=materials,
    )


async def material_detail(session: AsyncSession, material: Material) -> MaterialDetail:
    vector = None if material.embedding is None else list(material.embedding)
    challenges: list[RelatedChallenge] = []
    if vector is not None:
        hits = await nearest_challenges(session, vector, min_score=MIN_RELATED_SCORE)
        challenges = [
            RelatedChallenge(
                **ChallengeSummary.build(c).model_dump(), score=round(s, 4)
            )
            for c, s in hits
        ]
    return MaterialDetail(
        **MaterialSummary.build(material).model_dump(),
        source_section=material.source_section,
        updated_at=material.updated_at,
        related_innovations=await _related_innovations(session, vector),
        related_challenges=challenges,
    )


async def materials_for_vector(
    session: AsyncSession,
    vector: Sequence[float],
    *,
    limit: int = RELATED_MATERIALS,
    min_score: float = MIN_RELATED_SCORE,
) -> list[RelatedMaterial]:
    hits = await related_materials(session, vector, limit=limit, min_score=min_score)
    return [
        RelatedMaterial(**MaterialSummary.build(m).model_dump(), score=round(s, 4))
        for m, s in hits
    ]


async def challenges_for_vector(
    session: AsyncSession,
    vector: Sequence[float],
    *,
    limit: int = RELATED_CHALLENGES,
    min_score: float = MIN_RELATED_SCORE,
) -> list[RelatedChallenge]:
    hits = await nearest_challenges(session, vector, limit=limit, min_score=min_score)
    return [
        RelatedChallenge(**ChallengeSummary.build(c).model_dump(), score=round(s, 4))
        for c, s in hits
    ]
