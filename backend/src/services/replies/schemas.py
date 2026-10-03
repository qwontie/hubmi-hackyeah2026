from datetime import datetime
from typing import Literal

from pydantic import BaseModel

FragmentKind = Literal["opening", "innovation", "next_step", "closing"]


class InnovationRef(BaseModel):
    slug: str
    title: str
    url: str


class Fragment(BaseModel):
    id: str
    kind: FragmentKind
    label: str
    text: str
    innovation: InnovationRef | None = None


class EarlierAnswer(BaseModel):
    need_number: int
    need_excerpt: str
    body: str
    sent_at: datetime
    similarity: float
    demo: bool


class ReplySuggestions(BaseModel):
    fragments: list[Fragment]
    earlier_answers: list[EarlierAnswer]
    generated_at: datetime
