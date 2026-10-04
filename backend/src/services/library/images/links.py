from typing import Any, Literal, cast

from pydantic import BaseModel

from utils.db.models import ImageSource, Innovation

SourceName = Literal["rops", "youtube", "generated", "stock"]
STOCK = "stock"

LABELS = {
    ImageSource.ROPS.value: "Zdjęcie z materiałów ROPS",
    ImageSource.YOUTUBE.value: "Kadr z filmu ROPS",
    ImageSource.GENERATED.value: "Ilustracja AI",
    STOCK: "Ilustracja poglądowa",
}


PUBLIC_BASE = "/api/innovations"
ADMIN_BASE = "/api/admin/innovations"


def image_url(
    slug: str, version: int | None, *, card: bool = False, base: str = PUBLIC_BASE
) -> str | None:
    if version is None:
        return None
    size = "&size=card" if card else ""
    return f"{base}/{slug}/image?v={version}{size}"


class ImageFields(BaseModel):
    image_url: str | None = None
    image_card_url: str | None = None
    image_alt: str | None = None
    image_source: SourceName | None = None
    image_label: str | None = None


def image_fields(innovation: Innovation, base: str = PUBLIC_BASE) -> dict[str, Any]:
    version = innovation.image_version
    source = innovation.image_source if version is not None else None
    if version is None or source not in LABELS:
        return ImageFields().model_dump()
    return ImageFields(
        image_url=image_url(innovation.slug, version, base=base),
        image_card_url=image_url(innovation.slug, version, card=True, base=base),
        image_alt=innovation.image_alt,
        image_source=cast("SourceName", source),
        image_label=LABELS[source],
    ).model_dump()
