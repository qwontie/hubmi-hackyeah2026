import uuid
from dataclasses import dataclass

from sqlalchemy import func, update
from sqlmodel import col
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.db.models import ImageSource, Innovation, InnovationImage

from .links import STOCK
from .pictures import MIME_TYPE, Prepared


@dataclass(frozen=True, slots=True)
class Chosen:
    source: ImageSource
    prepared: Prepared
    alt: str
    source_url: str | None = None
    prompt: str | None = None
    model: str | None = None
    reused: bool = False


async def store(session: AsyncSession, innovation_id: uuid.UUID, chosen: Chosen) -> int:
    stored = await session.get(InnovationImage, innovation_id)
    version = (stored.version + 1) if stored else 1
    values = {
        "version": version,
        "source": chosen.source,
        "source_url": chosen.source_url,
        "image": chosen.prepared.image,
        "card": chosen.prepared.card,
        "mime_type": MIME_TYPE,
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
            image_source=STOCK if chosen.reused else chosen.source.value,
            image_alt=chosen.alt,
            updated_at=col(Innovation.updated_at),
        )
    )
    await session.commit()
    return version
