import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from utils.db.models import (
    FeedbackKind,
    IdeaStatus,
    MessageDelivery,
    MessageDirection,
    NeedOrigin,
    NeedStatus,
    SignupStatus,
    TesterRole,
)

REPLY_MAX = 5000
AUTHOR_MESSAGE_MAX = 2000

ReplyText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=REPLY_MAX)
]
AuthorText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=AUTHOR_MESSAGE_MAX
    ),
]


class AdminRef(BaseModel):
    id: uuid.UUID
    login: str


class ExpertRef(BaseModel):
    display_name: str
    expertise: str | None


class AdminMessage(BaseModel):
    id: uuid.UUID
    need_id: uuid.UUID | None
    idea_id: uuid.UUID | None
    application_id: uuid.UUID | None = None
    direction: MessageDirection
    body: str
    sent_at: datetime
    delivery_status: MessageDelivery | None
    admin: AdminRef | None
    read_at: datetime | None
    expert: ExpertRef | None = None


class PublicMessage(BaseModel):
    id: uuid.UUID
    direction: MessageDirection
    body: str
    sent_at: datetime
    author: Literal["rops", "expert", "author"] = "rops"
    expert: ExpertRef | None = None


class ClusterRef(BaseModel):
    id: uuid.UUID
    title: str
    size: int


class MatchRef(BaseModel):
    slug: str
    title: str
    score: float


class CategoryRef(BaseModel):
    slug: str
    name: str


class MatchInnovation(BaseModel):
    slug: str
    title: str
    lead: str
    category: CategoryRef


class MatchDetail(BaseModel):
    rank: int
    score: float
    reason: str
    innovation: MatchInnovation


class AdminNeed(BaseModel):
    id: uuid.UUID
    number: int | None
    text: str
    title: str | None
    origin: NeedOrigin
    powiat: str | None
    category_slug: str | None
    contact_email: str | None
    has_contact: bool
    status: NeedStatus
    nothing_fits: bool
    cluster: ClusterRef | None
    matches: list[MatchRef]
    unread: int
    messages_count: int
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminNeedDetail(AdminNeed):
    match_details: list[MatchDetail]
    messages: list[AdminMessage]
    can_email: bool


class NeedPage(BaseModel):
    items: list[AdminNeed]
    total: int
    page: int
    per_page: int


class StatusBody(BaseModel):
    status: NeedStatus


class NeedQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: NeedStatus | None = None
    cluster_id: uuid.UUID | None = None
    powiat: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    nothing_fits: bool | None = None
    unread: bool | None = None
    has_contact: bool | None = None
    q: str | None = Field(default=None, max_length=200)
    sort: Literal["newest", "oldest", "activity", "waiting"] = "newest"
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class ReplyBody(BaseModel):
    body: ReplyText


class AuthorMessageBody(BaseModel):
    body: AuthorText


class PublicNeed(BaseModel):
    id: uuid.UUID
    number: int | None
    text: str
    status: NeedStatus
    created_at: datetime


class PublicThread(BaseModel):
    need: PublicNeed
    messages: list[PublicMessage]
    can_email: bool


class PublicIdea(BaseModel):
    id: uuid.UUID
    number: int | None
    title: str
    status: IdeaStatus
    created_at: datetime


class PublicIdeaThread(BaseModel):
    idea: PublicIdea
    messages: list[PublicMessage]
    can_email: bool


class ContactInnovation(BaseModel):
    slug: str
    title: str


class ContactNeed(BaseModel):
    id: uuid.UUID
    number: int | None
    title: str | None
    text: str
    status: NeedStatus
    powiat: str | None
    created_at: datetime


class ContactIdea(BaseModel):
    id: uuid.UUID
    number: int | None
    title: str
    status: IdeaStatus
    powiat: str | None
    created_at: datetime


class ContactSignup(BaseModel):
    id: uuid.UUID
    innovation: ContactInnovation
    who: TesterRole
    organization: str | None
    powiat: str | None
    note: str
    status: SignupStatus
    created_at: datetime


class ContactFeedback(BaseModel):
    id: uuid.UUID
    innovation: ContactInnovation
    need_id: uuid.UUID
    kind: FeedbackKind
    created_at: datetime


class ContactProfile(BaseModel):
    email: str
    needs: list[ContactNeed]
    ideas: list[ContactIdea]
    test_signups: list[ContactSignup]
    feedback: list[ContactFeedback]


class ContactProfileRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
