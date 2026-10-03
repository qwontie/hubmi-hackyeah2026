import uuid
from typing import Any

from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.modules import InnovationRef, Page, offset
from services.search import nearest_innovations
from utils.db.models import Innovation
from utils.db.models.adaptation import Adaptation

from .schemas import (
    INSTITUTION_NAMES,
    AdaptationOut,
    AdminAdaptation,
    InstitutionOption,
    InstitutionType,
    Plan,
)

CANDIDATES = 6


def share_path(adaptation_id: uuid.UUID) -> str:
    return f"/adaptacja/{adaptation_id}"


def institution(slug: str) -> InstitutionOption:
    kind = InstitutionType(slug)
    return InstitutionOption(slug=kind, name=INSTITUTION_NAMES[kind])


async def candidates(session: AsyncSession, innovation: Innovation) -> list[Innovation]:
    if innovation.embedding is None:
        return []
    nearest = await nearest_innovations(
        session, innovation.embedding, limit=CANDIDATES, exclude_ids=(innovation.id,)
    )
    return [row for row, _score in nearest]


async def store(  # noqa: PLR0913
    session: AsyncSession,
    *,
    innovation: Innovation,
    institution_type: InstitutionType,
    place: str,
    powiat: str | None,
    context: str,
    plan: Plan,
    model: str,
) -> AdaptationOut:
    adaptation = Adaptation(
        innovation_id=innovation.id,
        institution_type=institution_type.value,
        place=place,
        powiat=powiat,
        context=context,
        plan=plan.model_dump(mode="json"),
        model=model,
    )
    session.add(adaptation)
    await session.commit()
    await session.refresh(adaptation)
    return to_out(adaptation, innovation)


def to_out(adaptation: Adaptation, innovation: Innovation) -> AdaptationOut:
    return AdaptationOut(
        id=adaptation.id,
        share_path=share_path(adaptation.id),
        innovation=InnovationRef.of(innovation),
        institution=institution(adaptation.institution_type),
        place=adaptation.place,
        powiat=adaptation.powiat,
        context=adaptation.context,
        plan=Plan.model_validate(adaptation.plan),
        created_at=adaptation.created_at,
    )


async def get(session: AsyncSession, adaptation_id: uuid.UUID) -> AdaptationOut | None:
    row = (
        await session.exec(
            select(Adaptation, Innovation)
            .join(Innovation, col(Innovation.id) == col(Adaptation.innovation_id))
            .where(Adaptation.id == adaptation_id)
        )
    ).first()
    if row is None:
        return None
    adaptation, innovation = row
    return to_out(adaptation, innovation)


async def list_admin(  # noqa: PLR0913
    session: AsyncSession,
    *,
    innovation: str | None,
    institution_type: InstitutionType | None,
    powiat: str | None,
    page: int,
    per_page: int,
) -> Page[AdminAdaptation]:
    filters: list[Any] = []
    if innovation:
        filters.append(Innovation.slug == innovation)
    if institution_type is not None:
        filters.append(Adaptation.institution_type == institution_type.value)
    if powiat:
        filters.append(Adaptation.powiat == powiat)
    join = col(Innovation.id) == col(Adaptation.innovation_id)
    total = await session.scalar(
        select(func.count())
        .select_from(Adaptation)
        .join(Innovation, join)
        .where(*filters)
    )
    rows = await session.exec(
        select(Adaptation, Innovation)
        .join(Innovation, join)
        .where(*filters)
        .order_by(col(Adaptation.created_at).desc())
        .offset(offset(page, per_page))
        .limit(per_page)
    )
    return Page(
        items=[
            AdminAdaptation(
                id=adaptation.id,
                share_path=share_path(adaptation.id),
                innovation=InnovationRef.of(inno),
                institution=institution(adaptation.institution_type),
                place=adaptation.place,
                powiat=adaptation.powiat,
                context=adaptation.context,
                service_name=str(adaptation.plan.get("service_name", "")),
                created_at=adaptation.created_at,
            )
            for adaptation, inno in rows
        ],
        total=total or 0,
        page=page,
        per_page=per_page,
    )
