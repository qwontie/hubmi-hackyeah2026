import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlmodel import col, delete

from services.tester import demand
from utils.db import session_scope
from utils.db.models import Category, Innovation
from utils.db.models.innovation import InnovationStatus


@pytest.fixture
async def innovation(database: None) -> AsyncGenerator[Innovation]:
    del database
    tag = uuid.uuid4().hex[:10]
    async with session_scope() as session:
        category = Category(
            slug=f"test-cat-{tag}", name="Test", source_url="https://rops.krakow.pl"
        )
        row = Innovation(
            slug=f"test-demand-{tag}",
            category_slug=category.slug,
            title="Popyt testowy",
            status=InnovationStatus.PUBLISHED,
        )
        session.add(category)
        await session.flush()
        session.add(row)
        await session.commit()
        await session.refresh(row)
        yield row
        await session.exec(delete(Innovation).where(col(Innovation.id) == row.id))
        await session.exec(delete(Category).where(col(Category.slug) == category.slug))
        await session.commit()


def test_key_follows_email_before_ip() -> None:
    by_mail = demand.client_key(email="A@x.pl", ip="10.0.0.1")
    assert by_mail == demand.client_key(email="a@x.pl", ip="10.0.0.2")
    assert by_mail != demand.client_key(email=None, ip="10.0.0.1")


async def test_one_per_person_per_day(innovation: Innovation) -> None:
    async with session_scope() as session:
        first = await demand.add(
            session,
            innovation_id=innovation.id,
            powiat="krakow",
            email=None,
            ip="10.9.9.9",
        )
        again = await demand.add(
            session,
            innovation_id=innovation.id,
            powiat="tarnow",
            email=None,
            ip="10.9.9.9",
        )
        other = await demand.add(
            session,
            innovation_id=innovation.id,
            powiat="krakow",
            email="mieszkanka@example.org",
            ip="10.9.9.9",
        )
        assert first is not None
        assert again is None
        assert other is not None
        assert other.consent_at is not None
        assert await demand.count(session, innovation.id) == 2
        grouped = await demand.by_powiat(
            session, innovation=innovation.slug, powiat=None, page=1, per_page=20
        )
        assert [(g.powiat, g.count, g.with_email) for g in grouped.items] == [
            ("krakow", 2, 1)
        ]
        assert grouped.items[0].powiat_name == "Kraków"
        listed = await demand.entries(
            session,
            innovation=innovation.slug,
            powiat="krakow",
            with_email=True,
            page=1,
            per_page=20,
        )
        assert [e.email for e in listed.items] == ["mieszkanka@example.org"]
