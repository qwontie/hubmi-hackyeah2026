import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from services.modules import InnovationRef
from utils.db.models.feedback import FeedbackKind
from utils.db.models.test_signup import SignupStatus, TesterRole

COMMENT_MAX = 1000
IMPROVEMENT_MIN = 10
IMPROVEMENT_MAX = 2000
NOTE_MAX = 1000
ORGANIZATION_MAX = 200
POWIAT_PATTERN = r"^[a-z0-9-]{2,60}$"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FeedbackIn(Strict):
    kind: Literal["fits", "does_not_fit"]
    need_id: uuid.UUID | None = None
    comment: str | None = Field(default=None, max_length=COMMENT_MAX)


class ImprovementIn(Strict):
    text: str = Field(max_length=IMPROVEMENT_MAX)


class TestSignupIn(Strict):
    who: TesterRole
    organization: str | None = Field(default=None, max_length=ORGANIZATION_MAX)
    powiat: str | None = Field(default=None, pattern=POWIAT_PATTERN)
    contact_email: str = Field(max_length=254)
    contact_consent: bool
    note: str | None = Field(default=None, max_length=NOTE_MAX)


class FeedbackSummary(BaseModel):
    fits: int
    does_not_fit: int
    improvements: int
    testers: int


class Votes(BaseModel):
    up: int = 0
    down: int = 0


class FeedbackOut(BaseModel):
    id: uuid.UUID
    kind: FeedbackKind
    votes: Votes
    summary: FeedbackSummary


class VoteRemoved(BaseModel):
    votes: Votes
    summary: FeedbackSummary


class Created(BaseModel):
    id: uuid.UUID


class AdminFeedback(BaseModel):
    id: uuid.UUID
    kind: FeedbackKind
    innovation: InnovationRef
    need_id: uuid.UUID | None
    comment: str | None
    created_at: datetime
    updated_at: datetime


class AdminTestSignup(BaseModel):
    id: uuid.UUID
    innovation: InnovationRef
    who: TesterRole
    organization: str | None
    powiat: str | None
    contact_email: str
    note: str
    status: SignupStatus
    created_at: datetime


class TestSignupPatch(Strict):
    status: SignupStatus


class InnovationFeedback(BaseModel):
    innovation: InnovationRef
    fits: int
    does_not_fit: int
    improvements: int
    testers: int
    last_at: datetime
