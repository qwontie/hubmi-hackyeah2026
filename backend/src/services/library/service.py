import re
import unicodedata
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ColumnElement, func, or_, select
from sqlmodel import col
from sqlmodel import select as entity_select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.errors import invalid, not_found
from services.bus import bus
from services.dialogue.audit import record
from services.ingest import refresh_embeddings
from utils.db.models import AdminUser, Category, Innovation, InnovationStatus
from utils.logging import logger

from .schemas import (
    AdminInnovation,
    AdminInnovationDetail,
    CategoryRef,
    InnovationChanges,
    InnovationCreate,
    InnovationQuery,
)

REQUIRED = frozenset(
    {
        "title",
        "category_slug",
        "lead",
        "what_it_is",
        "problems",
        "target_group",
        "who_can_use",
        "authors",
        "status",
    }
)
SLUG_LIMIT = 80
FOLD = str.maketrans({"ł": "l", "Ł": "L"})
MISSING = "Nie znaleziono innowacji."
UNKNOWN_CATEGORY = "Nieznana kategoria."


def slugify(title: str) -> str:
    folded = unicodedata.normalize("NFKD", title.translate(FOLD))
    ascii_text = folded.encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug[:SLUG_LIMIT].rstrip("-") or "innowacja"


def summary(innovation: Innovation, category: Category) -> AdminInnovation:
    return AdminInnovation(
        slug=innovation.slug,
        title=innovation.title,
        lead=innovation.lead,
        category=CategoryRef(slug=category.slug, name=category.name),
        status=innovation.status,
        has_video=bool(innovation.video_url),
        has_materials=bool(innovation.materials_url),
        source_url=innovation.source_url,
        edited_fields=list(innovation.edited_fields),
        edited_at=innovation.edited_at,
        imported_at=innovation.imported_at,
        updated_at=innovation.updated_at,
    )


def detail(innovation: Innovation, category: Category) -> AdminInnovationDetail:
    return AdminInnovationDetail(
        **summary(innovation, category).model_dump(),
        what_it_is=innovation.what_it_is,
        problems=innovation.problems,
        target_group=innovation.target_group,
        who_can_use=innovation.who_can_use,
        effectiveness=innovation.effectiveness,
        authors=list(innovation.authors),
        qr_url=innovation.qr_url,
        video_url=innovation.video_url,
        materials_url=innovation.materials_url,
        brochure_url=innovation.brochure_url,
        license=innovation.license,
        created_at=innovation.created_at,
    )


def public_summary(innovation: Innovation, category: Category) -> dict[str, Any]:
    return {
        "slug": innovation.slug,
        "title": innovation.title,
        "lead": innovation.lead,
        "category": {"slug": category.slug, "name": category.name},
        "has_video": bool(innovation.video_url),
        "has_materials": bool(innovation.materials_url),
        "status": innovation.status.value,
    }


def filters(query: InnovationQuery) -> list[ColumnElement[bool]]:
    found: list[ColumnElement[bool]] = []
    if query.status is not None:
        found.append(col(Innovation.status) == query.status)
    if query.category:
        found.append(col(Innovation.category_slug) == query.category)
    if query.edited is not None:
        edited = func.cardinality(col(Innovation.edited_fields)) > 0
        found.append(edited if query.edited else ~edited)
    text = (query.q or "").strip()
    if text:
        escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = func.hubmi_unaccent(f"%{escaped}%")
        found.append(
            or_(
                func.hubmi_unaccent(col(Innovation.title)).ilike(pattern, escape="\\"),
                func.hubmi_unaccent(col(Innovation.lead)).ilike(pattern, escape="\\"),
                col(Innovation.slug) == text,
            )
        )
    return found


async def list_innovations(
    session: AsyncSession, query: InnovationQuery
) -> tuple[list[AdminInnovation], int]:
    where = filters(query)
    total = await session.scalar(
        select(func.count()).select_from(Innovation).where(*where)
    )
    order = (
        [col(Innovation.updated_at).desc()]
        if query.sort == "updated"
        else [func.lower(col(Innovation.title))]
    )
    result = await session.exec(
        entity_select(Innovation, Category)
        .join(Category, col(Category.slug) == col(Innovation.category_slug))
        .where(*where)
        .order_by(*order, col(Innovation.id))
        .offset((query.page - 1) * query.per_page)
        .limit(query.per_page)
    )
    items = [summary(innovation, category) for innovation, category in result.all()]
    return items, int(total or 0)


async def find(session: AsyncSession, slug: str) -> tuple[Innovation, Category]:
    result = await session.exec(
        entity_select(Innovation, Category)
        .join(Category, col(Category.slug) == col(Innovation.category_slug))
        .where(col(Innovation.slug) == slug)
    )
    row = result.first()
    if row is None:
        raise not_found(MISSING)
    return row


async def category_of(session: AsyncSession, slug: str) -> Category:
    result = await session.exec(
        entity_select(Category).where(col(Category.slug) == slug)
    )
    category = result.first()
    if category is None:
        field = "category_slug"
        raise invalid(field, UNKNOWN_CATEGORY)
    return category


async def free_slug(session: AsyncSession, title: str) -> str:
    base = slugify(title)
    taken = set(
        (
            await session.exec(
                entity_select(Innovation.slug).where(
                    or_(
                        col(Innovation.slug) == base,
                        col(Innovation.slug).like(f"{base}-%"),
                    )
                )
            )
        ).all()
    )
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


async def reembed(session: AsyncSession) -> None:
    try:
        await refresh_embeddings(session)
    except Exception:
        await session.rollback()
        logger.exception("library: embedding refresh failed, search uses old vector")


async def announce(session: AsyncSession, slug: str) -> AdminInnovationDetail:
    innovation, category = await find(session, slug)
    bus.publish("innovation.updated", public_summary(innovation, category))
    return detail(innovation, category)


async def create(
    session: AsyncSession, admin: AdminUser, body: InnovationCreate
) -> AdminInnovationDetail:
    await category_of(session, body.category_slug)
    fields = body.model_dump()
    innovation = Innovation(
        **fields,
        slug=await free_slug(session, body.title),
        edited_fields=sorted(fields),
        edited_at=datetime.now(UTC),
    )
    session.add(innovation)
    await session.flush()
    record(
        session,
        admin,
        "innovation.create",
        target=("innovation", innovation.slug),
        details={"status": body.status.value},
    )
    await session.commit()
    await reembed(session)
    return await announce(session, innovation.slug)


async def update(
    session: AsyncSession, admin: AdminUser, slug: str, changes: InnovationChanges
) -> AdminInnovationDetail:
    innovation, _ = await find(session, slug)
    requested = changes.model_dump(exclude_unset=True)
    for name, value in requested.items():
        if value is None and name in REQUIRED:
            raise invalid(name, "To pole nie może być puste.")
    if "category_slug" in requested:
        await category_of(session, requested["category_slug"])
    changed = {
        name: value
        for name, value in requested.items()
        if getattr(innovation, name) != value
    }
    if not changed:
        return await announce(session, slug)
    before = {name: getattr(innovation, name) for name in changed}
    for name, value in changed.items():
        setattr(innovation, name, value)
    innovation.edited_fields = sorted(set(innovation.edited_fields) | set(changed))
    innovation.edited_at = datetime.now(UTC)
    session.add(innovation)
    record(
        session,
        admin,
        "innovation.update",
        target=("innovation", slug),
        details={
            "fields": sorted(changed),
            "status": {"from": str(before["status"]), "to": str(changed["status"])}
            if "status" in changed
            else None,
        },
    )
    await session.commit()
    if set(changed) - {"status"}:
        await reembed(session)
    return await announce(session, slug)


async def set_status(
    session: AsyncSession, admin: AdminUser, slug: str, status: InnovationStatus
) -> AdminInnovationDetail:
    return await update(session, admin, slug, InnovationChanges(status=status))
