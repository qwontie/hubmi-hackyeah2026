import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from utils.db.models.idea import IdeaStage, IdeaStatus

TITLE_MAX = 120
ESSENCE_MAX = 2000
FOR_WHOM_MAX = 500
CANVAS_FIELD_MAX = 1500
ANSWER_MAX = 1000
ANSWERS_MAX = 12
POWIAT_PATTERN = r"^[a-z0-9-]{2,60}$"

STAGE_NAMES: dict[IdeaStage, str] = {
    IdeaStage.IDEA: "Mam pomysł",
    IdeaStage.PREPARING: "Przygotowuję wdrożenie",
    IdeaStage.TESTING: "Testuję w małej skali",
    IdeaStage.RUNNING: "Działa i ma pierwsze efekty",
}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Canvas(Strict):
    problem: str | None = Field(default=None, max_length=CANVAS_FIELD_MAX)
    users: str | None = Field(default=None, max_length=CANVAS_FIELD_MAX)
    solution: str | None = Field(default=None, max_length=CANVAS_FIELD_MAX)
    novelty: str | None = Field(default=None, max_length=CANVAS_FIELD_MAX)
    resources: str | None = Field(default=None, max_length=CANVAS_FIELD_MAX)
    partners: str | None = Field(default=None, max_length=CANVAS_FIELD_MAX)
    micro_test: str | None = Field(default=None, max_length=CANVAS_FIELD_MAX)
    measures: str | None = Field(default=None, max_length=CANVAS_FIELD_MAX)


CANVAS_LABELS: dict[str, str] = {
    "problem": "Problem",
    "users": "Dla kogo",
    "solution": "Rozwiązanie",
    "novelty": "Co jest nowe",
    "resources": "Zasoby",
    "partners": "Partnerzy",
    "micro_test": "Test w małej skali",
    "measures": "Jak zmierzyć efekt",
}


class IdeaIn(Strict):
    title: str = Field(max_length=TITLE_MAX)
    essence: str = Field(max_length=ESSENCE_MAX)
    for_whom: str = Field(max_length=FOR_WHOM_MAX)
    stage: IdeaStage
    canvas: Canvas | None = None
    powiat: str | None = Field(default=None, pattern=POWIAT_PATTERN)
    contact_email: str | None = Field(default=None, max_length=254)
    contact_consent: bool = False


class IdeaPatch(Strict):
    title: str | None = Field(default=None, max_length=TITLE_MAX)
    essence: str | None = Field(default=None, max_length=ESSENCE_MAX)
    for_whom: str | None = Field(default=None, max_length=FOR_WHOM_MAX)
    stage: IdeaStage | None = None
    canvas: Canvas | None = None
    powiat: str | None = Field(default=None, pattern=POWIAT_PATTERN)
    contact_email: str | None = Field(default=None, max_length=254)
    contact_consent: bool | None = None


class Answer(Strict):
    question: str = Field(max_length=ANSWER_MAX)
    answer: str = Field(max_length=ANSWER_MAX)


class AssistIn(Strict):
    title: str | None = Field(default=None, max_length=TITLE_MAX)
    essence: str | None = Field(default=None, max_length=ESSENCE_MAX)
    for_whom: str | None = Field(default=None, max_length=FOR_WHOM_MAX)
    stage: IdeaStage | None = None
    canvas: Canvas | None = None
    answers: list[Answer] = Field(default_factory=list, max_length=ANSWERS_MAX)


class Question(BaseModel):
    field: str
    question: str


class Inspiration(BaseModel):
    slug: str
    title: str
    lead: str
    why: str


class AssistOut(BaseModel):
    questions: list[Question]
    suggestions: list[str]
    canvas: Canvas
    missing: list[str]
    inspirations: list[Inspiration]


class SimilarIdea(BaseModel):
    id: uuid.UUID
    number: int
    title: str
    essence: str
    stage: IdeaStage
    similarity: float


class SimilarInnovation(BaseModel):
    slug: str
    title: str
    lead: str
    similarity: float


class IdeaCreated(BaseModel):
    id: uuid.UUID
    number: int
    edit_token: str
    similar_ideas: list[SimilarIdea]
    similar_innovations: list[SimilarInnovation]


class PublicIdea(BaseModel):
    id: uuid.UUID
    number: int
    title: str
    essence: str
    for_whom: str
    stage: IdeaStage
    canvas: Canvas
    powiat: str | None
    created_at: datetime


class AuthorIdea(PublicIdea):
    status: IdeaStatus
    has_contact: bool
    updated_at: datetime


class AdminIdea(AuthorIdea):
    contact_email: str | None


class AdminIdeaDetail(AdminIdea):
    similar_ideas: list[SimilarIdea]
    similar_innovations: list[SimilarInnovation]


class IdeaStatusPatch(Strict):
    status: IdeaStatus


class StageOption(BaseModel):
    slug: IdeaStage
    name: str


class CanvasField(BaseModel):
    field: str
    name: str
