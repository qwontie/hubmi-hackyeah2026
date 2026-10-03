import uuid
from collections.abc import Collection
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.ai import AiUnavailableError, embed_documents
from services.ai.costs import AiBudgetExceededError
from services.modules import Page, offset
from services.search import nearest_innovations
from services.search.vector import cosine_distance
from utils.db.models.idea import Idea, IdeaStage, IdeaStatus
from utils.logging import logger

from .schemas import (
    AdminIdea,
    AdminIdeaDetail,
    AuthorIdea,
    Canvas,
    PublicIdea,
    SimilarIdea,
    SimilarInnovation,
)

SIMILAR_LIMIT = 3
SIMILAR_IDEA_MIN = 0.86
SIMILAR_INNOVATION_MIN = 0.80
PUBLIC_STATUSES = (IdeaStatus.ACCEPTED,)
EDITABLE_STATUSES = (IdeaStatus.NEW, IdeaStatus.IN_REVIEW)


def embedding_text(idea: Idea) -> str:
    return f"{idea.title}\n{idea.essence}\nDla kogo: {idea.for_whom}"


async def embed(idea: Idea) -> list[float] | None:
    try:
        return (await embed_documents([embedding_text(idea)], kind="idea_embed"))[0]
    except (AiUnavailableError, AiBudgetExceededError):
        logger.warning("idea %s stored without embedding", idea.id)
        return None


async def similar_ideas(
    session: AsyncSession,
    vector: list[float],
    *,
    exclude_id: uuid.UUID | None = None,
    statuses: Collection[IdeaStatus] | None = PUBLIC_STATUSES,
) -> list[SimilarIdea]:
    distance = cosine_distance(Idea.embedding, vector)
    query = select(Idea, (1 - distance).label("similarity")).where(
        col(Idea.embedding).is_not(None), distance <= 1 - SIMILAR_IDEA_MIN
    )
    if exclude_id is not None:
        query = query.where(Idea.id != exclude_id)
    if statuses is not None:
        query = query.where(col(Idea.status).in_(list(statuses)))
    rows = (await session.exec(query.order_by(distance).limit(SIMILAR_LIMIT))).all()
    return [
        SimilarIdea(
            id=idea.id,
            number=idea.number or 0,
            title=idea.title,
            essence=idea.essence,
            stage=idea.stage,
            similarity=round(float(similarity), 3),
        )
        for idea, similarity in rows
    ]


async def similar_innovations(
    session: AsyncSession, vector: list[float]
) -> list[SimilarInnovation]:
    rows = await nearest_innovations(session, vector, limit=SIMILAR_LIMIT)
    return [
        SimilarInnovation(
            slug=innovation.slug,
            title=innovation.title,
            lead=innovation.lead,
            similarity=round(similarity, 3),
        )
        for innovation, similarity in rows
        if similarity >= SIMILAR_INNOVATION_MIN
    ]


async def create(  # noqa: PLR0913
    session: AsyncSession,
    *,
    title: str,
    essence: str,
    for_whom: str,
    stage: IdeaStage,
    canvas: Canvas,
    powiat: str | None,
    contact_email: str | None,
    token_hash: str,
) -> Idea:
    idea = Idea(
        title=title,
        essence=essence,
        for_whom=for_whom,
        stage=stage,
        canvas=canvas.model_dump(exclude_none=True),
        powiat=powiat,
        contact_email=contact_email,
        contact_consent=contact_email is not None,
        consent_at=datetime.now(UTC) if contact_email else None,
        edit_token_hash=token_hash,
    )
    idea.embedding = await embed(idea)
    session.add(idea)
    await session.commit()
    await session.refresh(idea)
    return idea


async def get(session: AsyncSession, idea_id: uuid.UUID) -> Idea | None:
    return await session.get(Idea, idea_id)


async def save(session: AsyncSession, idea: Idea, *, reembed: bool) -> Idea:
    if reembed:
        idea.embedding = await embed(idea) or idea.embedding
    session.add(idea)
    await session.commit()
    await session.refresh(idea)
    return idea


def public_view(idea: Idea) -> PublicIdea:
    return PublicIdea(
        id=idea.id,
        number=idea.number or 0,
        title=idea.title,
        essence=idea.essence,
        for_whom=idea.for_whom,
        stage=idea.stage,
        canvas=Canvas.model_validate(idea.canvas),
        powiat=idea.powiat,
        created_at=idea.created_at,
    )


def author_view(idea: Idea) -> AuthorIdea:
    return AuthorIdea(
        **public_view(idea).model_dump(),
        status=idea.status,
        has_contact=idea.contact_email is not None,
        updated_at=idea.updated_at,
    )


def admin_view(idea: Idea) -> AdminIdea:
    return AdminIdea(**author_view(idea).model_dump(), contact_email=idea.contact_email)


async def admin_detail(session: AsyncSession, idea: Idea) -> AdminIdeaDetail:
    ideas: list[SimilarIdea] = []
    innovations: list[SimilarInnovation] = []
    if idea.embedding is not None:
        vector = list(idea.embedding)
        ideas = await similar_ideas(session, vector, exclude_id=idea.id, statuses=None)
        innovations = await similar_innovations(session, vector)
    return AdminIdeaDetail(
        **admin_view(idea).model_dump(),
        similar_ideas=ideas,
        similar_innovations=innovations,
    )


async def list_public(
    session: AsyncSession, *, stage: IdeaStage | None, page: int, per_page: int
) -> Page[PublicIdea]:
    filters: list[Any] = [col(Idea.status).in_(list(PUBLIC_STATUSES))]
    if stage is not None:
        filters.append(Idea.stage == stage)
    total = await session.scalar(select(func.count()).select_from(Idea).where(*filters))
    rows = await session.exec(
        select(Idea)
        .where(*filters)
        .order_by(col(Idea.created_at).desc())
        .offset(offset(page, per_page))
        .limit(per_page)
    )
    return Page(
        items=[public_view(idea) for idea in rows],
        total=total or 0,
        page=page,
        per_page=per_page,
    )


async def list_admin(  # noqa: PLR0913
    session: AsyncSession,
    *,
    status: IdeaStatus | None,
    stage: IdeaStage | None,
    powiat: str | None,
    q: str | None,
    page: int,
    per_page: int,
) -> Page[AdminIdea]:
    filters: list[Any] = []
    if status is not None:
        filters.append(Idea.status == status)
    if stage is not None:
        filters.append(Idea.stage == stage)
    if powiat:
        filters.append(Idea.powiat == powiat)
    if q:
        filters.append(
            or_(
                col(Idea.title).icontains(q, autoescape=True),
                col(Idea.essence).icontains(q, autoescape=True),
                col(Idea.for_whom).icontains(q, autoescape=True),
            )
        )
    total = await session.scalar(select(func.count()).select_from(Idea).where(*filters))
    rows = await session.exec(
        select(Idea)
        .where(*filters)
        .order_by(col(Idea.created_at).desc())
        .offset(offset(page, per_page))
        .limit(per_page)
    )
    return Page(
        items=[admin_view(idea) for idea in rows],
        total=total or 0,
        page=page,
        per_page=per_page,
    )
