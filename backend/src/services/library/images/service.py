import uuid
from dataclasses import dataclass
from datetime import datetime

import httpx
from sqlalchemy import func, update
from sqlalchemy import select as sa_select
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.visual.image import LITE_IMAGE_MODEL, draw
from utils.db.models import AiCall, ImageSource, Innovation, InnovationImage
from utils.logging import logger

from .describe import judge
from .pictures import Prepared, UnusableImageError, prepare
from .scene import image_prompt, write_scene
from .sources import Candidate, brochure_candidates, youtube_candidate

AI_KINDS = ("innovation_image_judge", "innovation_image_prompt", "innovation_image")
ALT_PREFIX = {
    ImageSource.ROPS: "Zdjęcie z materiałów ROPS",
    ImageSource.YOUTUBE: "Kadr z filmu ROPS",
}


@dataclass(frozen=True, slots=True)
class Chosen:
    source: ImageSource
    prepared: Prepared
    alt: str
    source_url: str | None = None
    prompt: str | None = None
    model: str | None = None


async def accept(
    candidate: Candidate, source: ImageSource, innovation: Innovation
) -> Chosen | None:
    try:
        prepared = prepare(candidate.data)
    except UnusableImageError:
        return None
    verdict = await judge(candidate.data, title=innovation.title, lead=innovation.lead)
    logger.info(
        "image %s %s %s usable=%s %s",
        innovation.slug,
        source.value,
        candidate.source_url,
        verdict.usable,
        verdict.reason,
    )
    if not verdict.usable:
        return None
    alt = verdict.alt[:1].lower() + verdict.alt[1:]
    return Chosen(
        source=source,
        prepared=prepared,
        alt=f"{ALT_PREFIX[source]}: {alt}.",
        source_url=candidate.source_url,
    )


async def real_image(http: httpx.AsyncClient, innovation: Innovation) -> Chosen | None:
    for candidate in await brochure_candidates(http, innovation.brochure_url):
        chosen = await accept(candidate, ImageSource.ROPS, innovation)
        if chosen is not None:
            return chosen
    candidate = await youtube_candidate(http, innovation.video_url)
    if candidate is not None:
        return await accept(candidate, ImageSource.YOUTUBE, innovation)
    return None


async def generated_image(innovation: Innovation) -> Chosen:
    scene = await write_scene(innovation)
    prompt = image_prompt(scene)
    picture = await draw(prompt, model=LITE_IMAGE_MODEL, kind="innovation_image")
    return Chosen(
        source=ImageSource.GENERATED,
        prepared=prepare(picture.data),
        alt=scene.alt,
        prompt=prompt,
        model=picture.model,
    )


async def store(session: AsyncSession, innovation_id: uuid.UUID, chosen: Chosen) -> int:
    stored = await session.get(InnovationImage, innovation_id)
    version = (stored.version + 1) if stored else 1
    values = {
        "version": version,
        "source": chosen.source,
        "source_url": chosen.source_url,
        "image": chosen.prepared.image,
        "card": chosen.prepared.card,
        "mime_type": "image/webp",
        "width": chosen.prepared.width,
        "height": chosen.prepared.height,
        "alt": chosen.alt,
        "prompt": chosen.prompt,
        "model": chosen.model,
    }
    if stored is None:
        session.add(
            InnovationImage.model_validate({"innovation_id": innovation_id, **values})
        )
        await session.flush()
    else:
        await session.exec(
            update(InnovationImage)
            .where(col(InnovationImage.innovation_id) == innovation_id)
            .values(**values, created_at=func.now())
        )
    await session.exec(
        update(Innovation)
        .where(col(Innovation.id) == innovation_id)
        .values(
            image_version=version,
            image_source=chosen.source.value,
            image_alt=chosen.alt,
            updated_at=col(Innovation.updated_at),
        )
    )
    await session.commit()
    return version


async def find_image(
    http: httpx.AsyncClient, innovation: Innovation, *, generate: bool
) -> Chosen | None:
    chosen = await real_image(http, innovation)
    if chosen is None and generate:
        chosen = await generated_image(innovation)
    return chosen


async def spent_since(session: AsyncSession, since: datetime) -> float:
    value = await session.scalar(
        sa_select(func.coalesce(func.sum(AiCall.cost_usd), 0)).where(
            col(AiCall.created_at) >= since, col(AiCall.kind).in_(AI_KINDS)
        )
    )
    return float(value or 0)


async def stored_image(
    session: AsyncSession, slug: str
) -> tuple[Innovation, InnovationImage] | None:
    row = (
        await session.exec(
            select(Innovation, InnovationImage)
            .join(InnovationImage, col(InnovationImage.innovation_id) == Innovation.id)
            .where(col(Innovation.slug) == slug)
        )
    ).first()
    return (row[0], row[1]) if row else None
