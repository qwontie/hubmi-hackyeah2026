import uuid
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from services.dialogue.schemas import AdminMessage
from services.kreator import AuthorIdea
from utils.db.models import AssignmentStatus, NeedStatus

NOTE_MAX = 1000
OPINION_MAX = 5000
PRIVATE_NOTE_MAX = 2000

Trimmed = StringConstraints(strip_whitespace=True, pattern=r"^[^\x00]*$")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExpertOut(BaseModel):
    id: uuid.UUID
    login: str
    display_name: str | None
    expertise: str | None
    has_email: bool
    open: int
    answered: int


class ExpertBrief(BaseModel):
    id: uuid.UUID | None
    display_name: str | None
    expertise: str | None
    email: str | None = None


class AssignmentOut(BaseModel):
    id: uuid.UUID
    kind: Literal["need", "idea"]
    need_id: uuid.UUID | None
    idea_id: uuid.UUID | None
    title: str
    expert: ExpertBrief
    note: str | None
    status: AssignmentStatus
    assigned_by: str
    opinions_count: int
    delivery_status: str | None = None
    created_at: datetime
    answered_at: datetime | None


class NoteOut(BaseModel):
    id: uuid.UUID
    body: str
    created_at: datetime


class AdminAssignment(AssignmentOut):
    private_notes: list[NoteOut]


class NeedItem(BaseModel):
    id: uuid.UUID
    number: int | None
    text: str
    title: str | None
    powiat: str | None
    category_slug: str | None
    status: NeedStatus
    created_at: datetime


class ExpertAssignmentDetail(AdminAssignment):
    item: AuthorIdea | NeedItem
    messages: list[AdminMessage]


class AssignBody(Strict):
    expert_id: uuid.UUID
    note: Annotated[str, Trimmed, Field(max_length=NOTE_MAX)] | None = None


class OpinionBody(Strict):
    body: Annotated[str, Trimmed, Field(max_length=OPINION_MAX)] | None = None
    private_note: Annotated[str, Trimmed, Field(max_length=PRIVATE_NOTE_MAX)] | None = (
        None
    )

    @model_validator(mode="after")
    def something(self) -> Self:
        if not self.body and not self.private_note:
            message = "Napisz opinię albo notatkę dla ROPS."
            raise ValueError(message)
        return self


class OpinionOut(BaseModel):
    message: AdminMessage | None
    private_note: NoteOut | None
    assignment: AssignmentOut


class ForwardBody(Strict):
    email: Annotated[str, Trimmed, Field(max_length=254)]
    name: Annotated[str, Trimmed, Field(max_length=200)] | None = None
    expertise: Annotated[str, Trimmed, Field(max_length=200)] | None = None
    note: Annotated[str, Trimmed, Field(max_length=NOTE_MAX)] | None = None


class ExpertContact(BaseModel):
    email: str
    name: str | None
    expertise: str | None
    assignments: int
    last_at: datetime


class AnswerIn(Strict):
    body: str = Field(max_length=OPINION_MAX * 2)
    website: str | None = Field(default=None, max_length=500)


class ExpertAnswerView(BaseModel):
    id: uuid.UUID
    kind: Literal["need", "idea"]
    title: str
    item: AuthorIdea | NeedItem
    note: str | None
    expert: ExpertBrief
    status: AssignmentStatus
    answers: list[NoteOut]
