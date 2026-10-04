from datetime import datetime

import httpx
from sqlalchemy import func
from sqlalchemy import select as sa_select
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.db.models import AiCall, ImageSource, Innovation, InnovationImage
from utils.logging import logger

from .describe import judge
from .pictures import UnusableImageError, prepare
from .sources import Candidate, brochure_candidates, youtube_candidate
from .storage import Chosen

AI_KINDS = ("innovation_image_judge",)
ALT_PREFIX = {
    ImageSource.ROPS: "Zdjęcie z materiałów ROPS",
    ImageSource.YOUTUBE: "Kadr z filmu ROPS",
}


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
