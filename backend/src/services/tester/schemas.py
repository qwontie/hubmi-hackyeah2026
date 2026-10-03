import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from services.modules import InnovationRef
from utils.db.models.feedback import FeedbackKind
from utils.db.models.message import MessageDelivery
from utils.db.models.test_signup import SignupStatus, TesterRole
from utils.db.models.volunteer import Recommendation, VolunteerMessageKind

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


class InnovationFeedback(BaseModel):
    innovation: InnovationRef
    fits: int
    does_not_fit: int
    improvements: int
    testers: int
    last_at: datetime


PROPOSAL_MIN = 20
PROPOSAL_MAX = 2000
REPORT_TEXT_MAX = 4000
PARTICIPANTS_MAX = 100_000
MESSAGE_MAX = 5000
REASON_MAX = 2000


class VolunteerIn(Strict):
    email: str = Field(max_length=254)
    contact_consent: bool
    powiat: str = Field(pattern=POWIAT_PATTERN)
    who: TesterRole
    organization: str | None = Field(default=None, max_length=ORGANIZATION_MAX)
    proposal: str = Field(max_length=PROPOSAL_MAX * 2)
    website: str | None = Field(default=None, max_length=500)


class VolunteerCreated(BaseModel):
    id: uuid.UUID
    duplicate: bool


class ReportIn(Strict):
    activity: str = Field(max_length=REPORT_TEXT_MAX * 2)
    participants: int = Field(ge=0, le=PARTICIPANTS_MAX)
    worked: str = Field(max_length=REPORT_TEXT_MAX * 2)
    not_worked: str = Field(max_length=REPORT_TEXT_MAX * 2)
    recommend: Recommendation


class VolunteerReportOut(BaseModel):
    activity: str
    participants: int
    worked: str
    not_worked: str
    recommend: Recommendation
    created_at: datetime
    updated_at: datetime


class VolunteerView(BaseModel):
    id: uuid.UUID
    innovation: InnovationRef
    powiat: str | None
    powiat_name: str | None
    proposal: str
    status: SignupStatus
    editable: bool
    report: VolunteerReportOut | None


class AdminVolunteer(BaseModel):
    id: uuid.UUID
    innovation: InnovationRef
    who: TesterRole
    organization: str | None
    powiat: str | None
    powiat_name: str | None
    email: str
    proposal: str
    status: SignupStatus
    decision_reason: str | None
    decided_at: datetime | None
    report: VolunteerReportOut | None
    created_at: datetime
    updated_at: datetime


class VolunteerMessageOut(BaseModel):
    id: uuid.UUID
    kind: VolunteerMessageKind
    body: str
    admin: str | None
    delivery_status: MessageDelivery
    delivery_error: str | None
    created_at: datetime


class VolunteerDrafts(BaseModel):
    accept: str
    reject: str


class AdminVolunteerDetail(AdminVolunteer):
    messages: list[VolunteerMessageOut]
    drafts: VolunteerDrafts


class VolunteerCounts(BaseModel):
    new: int = 0
    accepted: int = 0
    rejected: int = 0
    reported: int = 0
    closed: int = 0


class MessageIn(Strict):
    body: str = Field(max_length=MESSAGE_MAX * 2)


class AcceptIn(Strict):
    body: str | None = Field(default=None, max_length=MESSAGE_MAX * 2)


class RejectIn(Strict):
    reason: str = Field(max_length=REASON_MAX * 2)
    body: str | None = Field(default=None, max_length=MESSAGE_MAX * 2)


class RecommendCounts(BaseModel):
    yes: int = 0
    after_changes: int = 0
    no: int = 0


class InnovationReports(BaseModel):
    innovation: InnovationRef
    reports: int
    participants: int
    recommend: RecommendCounts
    items: list[AdminVolunteer]


class AdaptationVolunteers(BaseModel):
    innovation: InnovationRef
    powiat: str | None
    powiat_name: str | None
    count: int
    items: list[AdminVolunteer]


class DemandIn(Strict):
    powiat: str = Field(pattern=POWIAT_PATTERN)
    email: str | None = Field(default=None, max_length=254)
    contact_consent: bool = False
    website: str | None = Field(default=None, max_length=500)


class DemandCount(BaseModel):
    count: int


class DemandCreated(DemandCount):
    duplicate: bool


class DemandByPowiat(BaseModel):
    innovation: InnovationRef
    powiat: str
    powiat_name: str | None
    count: int
    with_email: int
    last_at: datetime


class DemandEntry(BaseModel):
    id: uuid.UUID
    innovation: InnovationRef
    powiat: str
    powiat_name: str | None
    email: str | None
    created_at: datetime
