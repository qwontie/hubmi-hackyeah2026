import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from utils.db.models.category import Category
from utils.db.models.challenge import Challenge
from utils.db.models.innovation import Innovation
from utils.db.models.material import (
    KnowledgeStatus,
    Material,
    MaterialKind,
    SummaryState,
)

from .topics import AREAS, KIND_NAMES, TOPICS


class Ref(BaseModel):
    slug: str
    name: str


class CountedRef(Ref):
    count: int


class FigureOut(BaseModel):
    label: str
    value: str
    unit: str
    year: int | None
    scope: str
    quote: str
    source_title: str
    document_title: str
    document_url: str
    page: int

    @classmethod
    def build(cls, raw: dict[str, Any]) -> "FigureOut":
        return cls(
            label=str(raw.get("label", "")),
            value=str(raw.get("value", "")),
            unit=str(raw.get("unit", "")),
            year=raw.get("year"),
            scope=str(raw.get("scope", "")),
            quote=str(raw.get("quote", "")),
            source_title=str(raw.get("source_title", "")),
            document_title=str(raw.get("document_title", "")),
            document_url=str(raw.get("document_url", "")),
            page=int(raw.get("page") or 0),
        )


class SourceOut(BaseModel):
    title: str
    url: str
    pages: list[int]


class MaterialSummary(BaseModel):
    id: uuid.UUID
    kind: Ref
    title: str
    year: int | None
    summary: str
    summary_ai: bool
    topics: list[Ref]
    file_url: str
    source_url: str
    pages: int | None
    file_size: int | None

    @classmethod
    def build(cls, material: Material) -> "MaterialSummary":
        return cls(
            id=material.id,
            kind=Ref(slug=material.kind.value, name=KIND_NAMES[material.kind.value]),
            title=material.title,
            year=material.year,
            summary=material.summary,
            summary_ai="summary" not in material.edited_fields,
            topics=[Ref(slug=t, name=TOPICS.get(t, t)) for t in material.topics],
            file_url=material.file_url,
            source_url=material.source_url,
            pages=material.pages,
            file_size=material.file_size,
        )


class RelatedInnovation(BaseModel):
    slug: str
    title: str
    lead: str
    category: Ref
    has_video: bool
    has_materials: bool
    score: float

    @classmethod
    def build(
        cls, innovation: Innovation, score: float, categories: dict[str, Category]
    ) -> "RelatedInnovation":
        category = categories.get(innovation.category_slug)
        return cls(
            slug=innovation.slug,
            title=innovation.title,
            lead=innovation.lead,
            category=Ref(
                slug=innovation.category_slug,
                name=category.name if category else innovation.category_slug,
            ),
            has_video=bool(innovation.video_url),
            has_materials=bool(innovation.materials_url),
            score=round(score, 4),
        )


class RelatedMaterial(MaterialSummary):
    score: float


class ChallengeSummary(BaseModel):
    id: uuid.UUID
    slug: str
    area: Ref
    title: str
    summary: str
    figures: list[FigureOut]
    verified: bool
    source: SourceOut

    @classmethod
    def build(cls, challenge: Challenge) -> "ChallengeSummary":
        return cls(
            id=challenge.id,
            slug=challenge.slug,
            area=Ref(
                slug=challenge.area, name=AREAS.get(challenge.area, challenge.area)
            ),
            title=challenge.title,
            summary=challenge.summary,
            figures=[FigureOut.build(f) for f in challenge.figures],
            verified=challenge.verified_at is not None,
            source=SourceOut(
                title=challenge.source_title,
                url=challenge.source_url,
                pages=list(challenge.source_pages),
            ),
        )


class RelatedChallenge(ChallengeSummary):
    score: float


class ChallengeDetail(ChallengeSummary):
    description: str
    verified_at: datetime | None
    updated_at: datetime
    related_innovations: list[RelatedInnovation]
    related_materials: list[RelatedMaterial]


class MaterialDetail(MaterialSummary):
    source_section: str
    updated_at: datetime
    related_innovations: list[RelatedInnovation]
    related_challenges: list[RelatedChallenge]


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    per_page: int


class AdminMaterial(MaterialSummary):
    status: KnowledgeStatus
    summary_state: SummaryState
    source_section: str
    edited_fields: list[str]
    edited_at: datetime | None
    imported_at: datetime | None
    updated_at: datetime

    @classmethod
    def build_admin(cls, material: Material) -> "AdminMaterial":
        return cls(
            **MaterialSummary.build(material).model_dump(),
            status=material.status,
            summary_state=material.summary_state,
            source_section=material.source_section,
            edited_fields=list(material.edited_fields),
            edited_at=material.edited_at,
            imported_at=material.imported_at,
            updated_at=material.updated_at,
        )


class AdminChallenge(ChallengeSummary):
    description: str
    position: int
    status: KnowledgeStatus
    verified_at: datetime | None
    verified_by: str | None
    edited_fields: list[str]
    edited_at: datetime | None
    imported_at: datetime | None
    updated_at: datetime

    @classmethod
    def build_admin(cls, challenge: Challenge) -> "AdminChallenge":
        return cls(
            **ChallengeSummary.build(challenge).model_dump(),
            description=challenge.description,
            position=challenge.position,
            status=challenge.status,
            verified_at=challenge.verified_at,
            verified_by=challenge.verified_by,
            edited_fields=list(challenge.edited_fields),
            edited_at=challenge.edited_at,
            imported_at=challenge.imported_at,
            updated_at=challenge.updated_at,
        )


def kind_refs(counts: dict[str, int]) -> list[CountedRef]:
    return [
        CountedRef(
            slug=kind.value,
            name=KIND_NAMES[kind.value],
            count=counts.get(kind.value, 0),
        )
        for kind in MaterialKind
    ]
