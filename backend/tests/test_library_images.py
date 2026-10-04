import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

import pytest
from sqlmodel import col, delete, select

from api.errors import ApiError
from services.ingest import importer
from services.library import service
from services.library.images import image_fields
from services.library.images.stock import give_stock, target
from services.library.schemas import PictureChoice
from utils.db import session_scope
from utils.db.models import (
    AdminAction,
    AdminRole,
    AdminUser,
    Category,
    ImageSource,
    Innovation,
    InnovationImage,
)
from utils.db.models.import_run import ImportRun, ImportTrigger
from utils.db.models.innovation import EMBEDDING_DIMENSIONS, InnovationStatus


def axis(*weights: tuple[int, float]) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for index, value in weights:
        vector[index] = value
    return vector


@dataclass
class Pool:
    tag: str
    category: str
    photo: Innovation
    drawing: Innovation
    copy: Innovation
    admin: AdminUser
    created: list[uuid.UUID]
    categories: list[str]


async def add_item(
    session: Any,
    slug: str,
    category: str,
    embedding: list[float] | None,
    source: ImageSource | None = None,
) -> Innovation:
    innovation = Innovation(
        slug=slug,
        category_slug=category,
        title=f"Rozwiązanie {slug}",
        status=InnovationStatus.PUBLISHED,
        embedding=embedding,
    )
    if source is not None:
        innovation.image_version = 1
        innovation.image_source = source.value
        innovation.image_alt = f"Opis {slug}"
    session.add(innovation)
    await session.flush()
    if source is not None:
        session.add(
            InnovationImage(
                innovation_id=innovation.id,
                version=1,
                source=source,
                image=f"full {slug}".encode(),
                card=f"card {slug}".encode(),
                mime_type="image/webp",
                width=1280,
                height=720,
                alt=f"Opis {slug}",
            )
        )
    await session.commit()
    await session.refresh(innovation)
    return innovation


@pytest.fixture
async def pool(database: None) -> AsyncGenerator[Pool]:
    del database
    tag = uuid.uuid4().hex[:10]
    category = f"test-img-{tag}"
    async with session_scope() as session:
        session.add(
            Category(slug=category, name="Test", source_url="https://rops.krakow.pl")
        )
        admin = AdminUser(
            login=f"test-admin-{tag}",
            password_hash="x",  # noqa: S106
            role=AdminRole.ADMIN,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        photo = await add_item(
            session, f"test-photo-{tag}", category, axis((0, 1.0)), ImageSource.ROPS
        )
        drawing = await add_item(
            session,
            f"test-drawing-{tag}",
            category,
            axis((1, 1.0)),
            ImageSource.GENERATED,
        )
        copy = await add_item(
            session,
            f"test-copy-{tag}",
            category,
            axis((0, 0.1), (1, 0.9)),
            ImageSource.ROPS,
        )
        copy.image_source = "stock"
        session.add(copy)
        await session.commit()
    world = Pool(
        tag=tag,
        category=category,
        photo=photo,
        drawing=drawing,
        copy=copy,
        admin=admin,
        created=[photo.id, drawing.id, copy.id],
        categories=[category],
    )
    yield world
    async with session_scope() as session:
        await session.exec(
            delete(Innovation).where(col(Innovation.id).in_(world.created))
        )
        await session.exec(
            delete(Category).where(col(Category.slug).in_(world.categories))
        )
        await session.exec(
            delete(AdminAction).where(col(AdminAction.admin_id) == admin.id)
        )
        await session.exec(delete(AdminUser).where(col(AdminUser.id) == admin.id))
        await session.commit()


async def picture(innovation_id: uuid.UUID) -> tuple[Innovation, InnovationImage]:
    async with session_scope() as session:
        row = (
            await session.exec(
                select(Innovation, InnovationImage)
                .join(
                    InnovationImage, col(InnovationImage.innovation_id) == Innovation.id
                )
                .where(col(Innovation.id) == innovation_id)
            )
        ).one()
    return row[0], row[1]


async def test_new_item_takes_the_nearest_original_of_its_category(pool: Pool) -> None:
    async with session_scope() as session:
        fresh = await add_item(
            session, f"test-new-{pool.tag}", pool.category, axis((0, 0.1), (1, 0.9))
        )
        pool.created.append(fresh.id)
        assert await give_stock(session, target(fresh))

    innovation, image = await picture(fresh.id)
    assert image.image == f"full {pool.drawing.slug}".encode()
    assert image.card == f"card {pool.drawing.slug}".encode()
    assert image.source == ImageSource.GENERATED
    assert innovation.image_source == "stock"
    assert innovation.image_alt == f"Opis {pool.drawing.slug}"
    fields = image_fields(innovation)
    assert fields["image_source"] == "stock"
    assert fields["image_label"] == "Ilustracja poglądowa"
    assert fields["image_url"] == f"/api/innovations/{fresh.slug}/image?v=1"


async def test_import_gives_a_picture_to_a_new_item_in_an_empty_category(
    pool: Pool, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = f"test-empty-{pool.tag}"
    pool.categories.append(empty)
    slug = f"test-imported-{pool.tag}"

    async def crawl(session: Any, *_: Any) -> None:
        session.add(
            Category(slug=empty, name="Pusta", source_url="https://rops.krakow.pl")
        )
        await session.flush()
        session.add(Innovation(slug=slug, category_slug=empty, title="Nowe"))
        await session.commit()

    async def embeddings_down(*_: Any) -> int:
        message = "embeddings are down"
        raise RuntimeError(message)

    monkeypatch.setattr(importer, "_crawl", crawl)
    monkeypatch.setattr(importer, "refresh_embeddings", embeddings_down)
    run = await importer.run_import(trigger=ImportTrigger.SCRIPT)

    async with session_scope() as session:
        fresh = (
            await session.exec(select(Innovation).where(col(Innovation.slug) == slug))
        ).one()
        pool.created.append(fresh.id)
        await session.exec(delete(ImportRun).where(col(ImportRun.id) == run.id))
        await session.commit()
    assert run.error is not None
    innovation, image = await picture(fresh.id)
    assert innovation.image_source == "stock"
    assert innovation.image_version == 1
    assert image.image
    assert image.alt == innovation.image_alt


async def test_staff_replace_a_picture_from_the_pool(pool: Pool) -> None:
    async with session_scope() as session:
        listed = await service.picture_pool(session)
    ids = {item.id for item in listed}
    assert {pool.photo.slug, pool.drawing.slug} <= ids
    assert pool.copy.slug not in ids
    assert all(item.image_source != "stock" for item in listed)

    async with session_scope() as session:
        updated = await service.set_picture(
            session, pool.admin, pool.copy.slug, PictureChoice(pool_id=pool.photo.slug)
        )
    assert updated.image_source == "stock"
    assert updated.image_url == f"/api/admin/innovations/{pool.copy.slug}/image?v=2"
    _, image = await picture(pool.copy.id)
    assert image.image == f"full {pool.photo.slug}".encode()
    assert image.version == 2

    for wrong in (pool.copy.slug, pool.drawing.slug, f"test-missing-{pool.tag}"):
        async with session_scope() as session:
            with pytest.raises(ApiError) as error:
                await service.set_picture(
                    session, pool.admin, pool.drawing.slug, PictureChoice(pool_id=wrong)
                )
        assert error.value.status_code == 422
    _, untouched = await picture(pool.drawing.id)
    assert untouched.image == f"full {pool.drawing.slug}".encode()
