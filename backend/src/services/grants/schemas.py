import uuid
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from utils.db.models import ApplicationStatus, GrantCallStatus

SECTIONS_MAX = 20
KEY_PATTERN = r"^[a-z][a-z0-9_]{1,40}$"

NO_NUL = r"^[^\x00]*$"
Trimmed = StringConstraints(strip_whitespace=True, pattern=NO_NUL)
Phase = Literal["upcoming", "open", "closed"]
SectionSource = Literal["empty", "idea", "ai", "author"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GrantSection(Strict):
    key: str = Field(pattern=KEY_PATTERN)
    label: Annotated[str, Trimmed, Field(min_length=2, max_length=200)]
    hint: Annotated[str, Trimmed, Field(max_length=1000)] = ""
    max_length: int = Field(ge=100, le=10000)
    required: bool = True


def unique_keys(sections: list[GrantSection] | None) -> None:
    if sections is None:
        return
    keys = [s.key for s in sections]
    if len(keys) != len(set(keys)):
        message = "Klucze sekcji muszą być różne."
        raise ValueError(message)


class GrantTemplateOut(BaseModel):
    slug: str
    title: str
    description: str
    source_url: str
    sections: list[GrantSection]


class GrantCallOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    opens_at: datetime
    closes_at: datetime
    phase: Phase
    source_url: str | None
    demo: bool
    sections: list[GrantSection]
    updated_at: datetime


class ApplicationCounts(BaseModel):
    total: int = 0
    submitted: int = 0
    in_review: int = 0
    accepted: int = 0
    rejected: int = 0


class AdminGrantCall(GrantCallOut):
    status: GrantCallStatus
    template: str | None
    applications: ApplicationCounts
    created_at: datetime


class CallIn(Strict):
    title: Annotated[str, Trimmed, Field(min_length=5, max_length=200)]
    description: Annotated[str, Trimmed, Field(min_length=10, max_length=10000)]
    opens_at: datetime
    closes_at: datetime
    source_url: AnyHttpUrl | None = None
    sections: list[GrantSection] | None = Field(default=None, max_length=SECTIONS_MAX)
    template: str | None = Field(default=None, max_length=100)
    status: Literal["draft", "published"] = "draft"

    @model_validator(mode="after")
    def check(self) -> Self:
        unique_keys(self.sections)
        if self.closes_at <= self.opens_at:
            message = "Data zamknięcia musi być późniejsza niż data otwarcia."
            raise ValueError(message)
        return self


class CallPatch(Strict):
    title: Annotated[str, Trimmed, Field(min_length=5, max_length=200)] | None = None
    description: (
        Annotated[str, Trimmed, Field(min_length=10, max_length=10000)] | None
    ) = None
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    source_url: AnyHttpUrl | None = None
    sections: list[GrantSection] | None = Field(default=None, max_length=SECTIONS_MAX)
    status: GrantCallStatus | None = None

    @model_validator(mode="after")
    def check(self) -> Self:
        unique_keys(self.sections)
        return self


class CallRef(BaseModel):
    id: uuid.UUID
    title: str
    opens_at: datetime
    closes_at: datetime
    phase: Phase
    demo: bool


class IdeaRef(BaseModel):
    id: uuid.UUID
    number: int
    title: str


class ApplicationSection(BaseModel):
    key: str
    label: str
    hint: str
    max_length: int
    required: bool
    text: str
    missing: list[str]
    source: SectionSource


class ApplicationOut(BaseModel):
    id: uuid.UUID
    number: int
    call: CallRef
    idea: IdeaRef | None
    contact_email: str | None
    contact_consent: bool
    status: ApplicationStatus
    sections: list[ApplicationSection]
    missing_required: list[str]
    pdf_url: str
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ApplicationCreated(ApplicationOut):
    edit_token: str


class AdminApplication(ApplicationOut):
    idea_contact: bool


class AdminApplicationSummary(BaseModel):
    id: uuid.UUID
    number: int
    call_id: uuid.UUID
    idea: IdeaRef | None
    status: ApplicationStatus
    missing_required: list[str]
    submitted_at: datetime | None
    updated_at: datetime


class ApplicationPage(BaseModel):
    items: list[AdminApplicationSummary]
    total: int
    page: int
    per_page: int


class CallPage(BaseModel):
    items: list[AdminGrantCall]
    total: int
    page: int
    per_page: int


class ContactIn(Strict):
    contact_email: Annotated[str, Trimmed, Field(max_length=254)] | None = None
    contact_consent: bool | None = None


class StartIn(ContactIn):
    idea_id: uuid.UUID | None = None


class SectionsPatch(ContactIn):
    sections: dict[
        Annotated[str, Field(pattern=KEY_PATTERN)],
        Annotated[str, Field(max_length=10000, pattern=NO_NUL)],
    ] = Field(default_factory=dict, max_length=SECTIONS_MAX)


class RedraftIn(Strict):
    keys: list[Annotated[str, Field(pattern=KEY_PATTERN)]] | None = Field(
        default=None, max_length=SECTIONS_MAX
    )


class StatusIn(Strict):
    status: Literal["in_review", "accepted", "rejected"]


class SubscribeIn(Strict):
    email: Annotated[str, Trimmed, Field(min_length=3, max_length=254)]
    consent: bool


class TokenIn(Strict):
    token: Annotated[str, Trimmed, Field(min_length=10, max_length=200)]


class SubscriptionOut(BaseModel):
    status: Literal["pending", "confirmed", "unsubscribed"]
