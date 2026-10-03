from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlmodel.ext.asyncio.session import AsyncSession

from services.ai import AiBudgetExceededError, AiUnavailableError
from utils.db.models.admin_user import AdminUser
from utils.db.models.challenge import Challenge
from utils.db.models.material import KnowledgeStatus, Material, MaterialKind
from utils.logging import logger

from .embeddings import refresh_challenge_embeddings
from .materials import refresh_material_embeddings
from .topics import AREAS, TOPICS

ShortText = Annotated[str, Field(min_length=1, max_length=300)]
LongText = Annotated[str, Field(max_length=6000)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MaterialPatch(Strict):
    title: ShortText | None = None
    kind: MaterialKind | None = None
    year: Annotated[int, Field(ge=1990, le=2100)] | None = None
    summary: LongText | None = None
    topics: Annotated[list[str], Field(max_length=6)] | None = None
    status: KnowledgeStatus | None = None

    @field_validator("topics")
    @classmethod
    def known_topics(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        unknown = [t for t in value if t not in TOPICS]
        if unknown:
            msg = "unknown topic"
            raise ValueError(msg)
        return list(dict.fromkeys(value))


class FigureIn(Strict):
    label: ShortText
    value: Annotated[str, Field(min_length=1, max_length=60)]
    unit: Annotated[str, Field(max_length=40)] = ""
    year: Annotated[int, Field(ge=1990, le=2100)] | None = None
    scope: Annotated[str, Field(max_length=60)] = ""
    quote: Annotated[str, Field(max_length=600)] = ""
    source_title: Annotated[str, Field(max_length=300)] = ""
    document_title: Annotated[str, Field(max_length=300)] = ""
    document_url: Annotated[str, Field(min_length=8, max_length=600)]
    page: Annotated[int, Field(ge=1, le=5000)]


class ChallengePatch(Strict):
    title: ShortText | None = None
    summary: LongText | None = None
    description: LongText | None = None
    area: str | None = None
    position: Annotated[int, Field(ge=0, le=10_000)] | None = None
    figures: Annotated[list[FigureIn], Field(max_length=20)] | None = None
    status: KnowledgeStatus | None = None
    verified: bool | None = None

    @field_validator("area")
    @classmethod
    def known_area(cls, value: str | None) -> str | None:
        if value is not None and value not in AREAS:
            msg = "unknown area"
            raise ValueError(msg)
        return value


EMBEDDED_MATERIAL = {"title", "summary", "topics"}
EMBEDDED_CHALLENGE = {"title", "summary", "description", "area"}
NOT_CONTENT = {"status", "verified"}


def _apply(target: Material | Challenge, values: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    for name, value in values.items():
        if getattr(target, name) != value:
            setattr(target, name, value)
            changed.append(name)
    content = [name for name in changed if name not in NOT_CONTENT]
    if content:
        target.edited_fields = sorted({*target.edited_fields, *content})
        target.edited_at = datetime.now(UTC)
    return changed


async def _reembed(session: AsyncSession, *, material: bool) -> None:
    try:
        if material:
            await refresh_material_embeddings(session)
        else:
            await refresh_challenge_embeddings(session)
    except (AiUnavailableError, AiBudgetExceededError):
        logger.warning("knowledge: re-embedding postponed to the next import")


async def patch_material(
    session: AsyncSession, material: Material, patch: MaterialPatch
) -> list[str]:
    values = {
        name: getattr(patch, name)
        for name in patch.model_fields_set
        if getattr(patch, name) is not None or name == "year"
    }
    changed = _apply(material, values)
    session.add(material)
    await session.commit()
    if EMBEDDED_MATERIAL & set(changed):
        await _reembed(session, material=True)
    await session.refresh(material)
    return changed


async def patch_challenge(
    session: AsyncSession, challenge: Challenge, patch: ChallengePatch, admin: AdminUser
) -> list[str]:
    values: dict[str, Any] = {
        name: getattr(patch, name)
        for name in patch.model_fields_set
        if name != "verified" and getattr(patch, name) is not None
    }
    if "figures" in values:
        values["figures"] = [f.model_dump() for f in patch.figures or []]
    changed = _apply(challenge, values)
    if patch.verified is not None:
        verified = challenge.verified_at is not None
        if patch.verified and not verified:
            challenge.verified_at = datetime.now(UTC)
            challenge.verified_by = admin.login
            changed.append("verified")
        if not patch.verified and verified:
            challenge.verified_at = None
            challenge.verified_by = None
            changed.append("verified")
    session.add(challenge)
    await session.commit()
    if EMBEDDED_CHALLENGE & set(changed):
        await _reembed(session, material=False)
    await session.refresh(challenge)
    return changed
