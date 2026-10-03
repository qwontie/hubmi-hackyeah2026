import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel


class Period(StrEnum):
    WEEK = "7d"
    MONTH = "30d"
    QUARTER = "90d"
    YEAR = "365d"

    @property
    def days(self) -> int:
        return int(self.value.removesuffix("d"))


class Range(BaseModel):
    period: Period
    start: datetime
    end: datetime
    previous_start: datetime
    timezone: str


class Totals(BaseModel):
    needs: int
    needs_previous: int
    nothing_fits: int
    nothing_fits_share: float
    waiting: int
    answered: int
    closed: int
    with_contact: int
    author_messages: int
    replies: int
    median_first_reply_hours: float | None


class SeriesPoint(BaseModel):
    start: date
    needs: int
    nothing_fits: int


class Bucket(BaseModel):
    slug: str | None
    name: str
    count: int


class ClusterTrend(BaseModel):
    id: uuid.UUID
    title: str
    size: int
    current: int
    previous: int
    growth: int


class InnovationUsage(BaseModel):
    slug: str
    title: str
    matches: int
    top_matches: int
    avg_score: float


class AiKind(BaseModel):
    kind: str
    calls: int
    failed: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    avg_latency_ms: float | None


class AiDay(BaseModel):
    start: date
    calls: int
    cost_usd: float


class AiSpend(BaseModel):
    calls: int
    failed: int
    cost_usd: float
    by_kind: list[AiKind]
    per_day: list[AiDay]


class InnovationFeedback(BaseModel):
    slug: str
    title: str
    fits: int
    does_not_fit: int


class FeedbackStats(BaseModel):
    fits: int
    does_not_fit: int
    fit_share: float | None
    improvements: int
    test_signups: int
    most_rejected: list[InnovationFeedback]


class Stats(BaseModel):
    range: Range
    totals: Totals
    per_day: list[SeriesPoint]
    per_week: list[SeriesPoint]
    by_category: list[Bucket]
    by_powiat: list[Bucket]
    top_clusters: list[ClusterTrend]
    growing_clusters: list[ClusterTrend]
    top_innovations: list[InnovationUsage]
    feedback: FeedbackStats
    ai: AiSpend
