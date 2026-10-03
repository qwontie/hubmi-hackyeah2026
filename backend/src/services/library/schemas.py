from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from utils.db.models import InnovationStatus

Title = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)
]
Slug = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
Section = Annotated[str, StringConstraints(strip_whitespace=True, max_length=20000)]
Author = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)
]
Link = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, max_length=1000, pattern=r"^https?://\S+$"
    ),
]
License = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]


class CategoryRef(BaseModel):
    slug: str
    name: str


class AdminInnovation(BaseModel):
    slug: str
    title: str
    lead: str
    category: CategoryRef
    status: InnovationStatus
    has_video: bool
    has_materials: bool
    source_url: str | None
    edited_fields: list[str]
    edited_at: datetime | None
    imported_at: datetime | None
    updated_at: datetime


class AdminInnovationDetail(AdminInnovation):
    what_it_is: str
    problems: str
    target_group: str
    who_can_use: str
    effectiveness: str | None
    authors: list[str]
    qr_url: str | None
    video_url: str | None
    materials_url: str | None
    brochure_url: str | None
    license: str | None
    created_at: datetime


class InnovationPage(BaseModel):
    items: list[AdminInnovation]
    total: int
    page: int
    per_page: int


class InnovationQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: InnovationStatus | None = None
    category: str | None = Field(default=None, max_length=100)
    edited: bool | None = None
    q: str | None = Field(default=None, max_length=200)
    sort: Literal["title", "updated"] = "title"
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class InnovationChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    category_slug: Slug | None = None
    lead: Section | None = None
    what_it_is: Section | None = None
    problems: Section | None = None
    target_group: Section | None = None
    who_can_use: Section | None = None
    effectiveness: Section | None = None
    authors: list[Author] | None = Field(default=None, max_length=30)
    video_url: Link | None = None
    materials_url: Link | None = None
    brochure_url: Link | None = None
    license: License | None = None
    status: InnovationStatus | None = None


class InnovationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    category_slug: Slug
    lead: Section = ""
    what_it_is: Section = ""
    problems: Section = ""
    target_group: Section = ""
    who_can_use: Section = ""
    effectiveness: Section | None = None
    authors: list[Author] = Field(default_factory=list, max_length=30)
    video_url: Link | None = None
    materials_url: Link | None = None
    brochure_url: Link | None = None
    license: License | None = None
    status: InnovationStatus = InnovationStatus.DRAFT
