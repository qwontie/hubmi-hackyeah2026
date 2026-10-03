import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from services.needs import POWIATS
from utils.db.models.category import Category
from utils.db.models.innovation import Innovation

TERMS_URL = (
    "https://rops.krakow.pl/mpliki/IS/BIBLIOTEKA_INNOWACJI_SPOECZNYCH/"
    "Zasady_wykorzystania_innowacji_MIIS.pdf"
)
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")


def _powiat(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if value not in POWIATS:
        msg = "unknown powiat"
        raise ValueError(msg)
    return value


def _email(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    value = value.strip()
    if len(value) > 254 or not EMAIL.match(value):  # noqa: PLR2004
        msg = "invalid email"
        raise ValueError(msg)
    return value


Powiat = Annotated[str | None, AfterValidator(_powiat)]
Email = Annotated[str | None, AfterValidator(_email)]
NeedText = Annotated[str, Field(max_length=4000)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CategoryRef(BaseModel):
    slug: str
    name: str


class CategoryOut(CategoryRef):
    count: int
    icon_url: str | None


class PowiatOut(BaseModel):
    slug: str
    name: str


class InnovationSummary(BaseModel):
    slug: str
    title: str
    lead: str
    category: CategoryRef
    has_video: bool
    has_materials: bool

    @classmethod
    def build(
        cls, innovation: Innovation, categories: dict[str, Category]
    ) -> "InnovationSummary":
        category = categories.get(innovation.category_slug)
        return cls(
            slug=innovation.slug,
            title=innovation.title,
            lead=innovation.lead,
            category=CategoryRef(
                slug=innovation.category_slug,
                name=category.name if category else innovation.category_slug,
            ),
            has_video=bool(innovation.video_url),
            has_materials=bool(innovation.materials_url),
        )


class InnovationDetail(InnovationSummary):
    what_it_is: str
    problems: str
    target_group: str
    who_can_use: str
    effectiveness: str | None
    authors: list[str]
    video_url: str | None
    materials_url: str | None
    brochure_url: str | None
    license: str | None
    qr_url: str | None
    terms_url: str
    source_url: str | None
    updated_at: datetime

    @classmethod
    def build_detail(
        cls, innovation: Innovation, categories: dict[str, Category]
    ) -> "InnovationDetail":
        summary = InnovationSummary.build(innovation, categories)
        return cls(
            **summary.model_dump(),
            what_it_is=innovation.what_it_is,
            problems=innovation.problems,
            target_group=innovation.target_group,
            who_can_use=innovation.who_can_use,
            effectiveness=innovation.effectiveness,
            authors=innovation.authors,
            video_url=innovation.video_url,
            materials_url=innovation.materials_url,
            brochure_url=innovation.brochure_url,
            license=innovation.license,
            qr_url=innovation.qr_url,
            terms_url=TERMS_URL,
            source_url=innovation.source_url,
            updated_at=innovation.updated_at,
        )


class InnovationPage(BaseModel):
    items: list[InnovationSummary]
    total: int
    page: int
    per_page: int


class ClusterRef(BaseModel):
    id: uuid.UUID
    title: str
    size: int


class MatchIn(StrictModel):
    text: NeedText
    powiat: Powiat = None


class NeedRef(BaseModel):
    id: uuid.UUID
    number: int
    edit_token: str


class MatchItem(BaseModel):
    innovation: InnovationSummary
    score: float
    reason: str


class MatchOut(BaseModel):
    need: NeedRef
    results: list[MatchItem]
    similar_count: int
    cluster: ClusterRef | None
    degraded: bool


class NeedIn(StrictModel):
    text: NeedText
    powiat: Powiat = None
    contact_email: Email = None
    contact_consent: bool = False


class NeedOut(BaseModel):
    id: uuid.UUID
    number: int
    edit_token: str
    similar_count: int
    cluster: ClusterRef | None


class NeedPatch(StrictModel):
    powiat: Powiat = None
    contact_email: Email = None
    contact_consent: bool | None = None
    nothing_fits: bool | None = None


class NeedPatched(BaseModel):
    id: uuid.UUID
    status: str
