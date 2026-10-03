from dataclasses import dataclass, field

from sqlalchemy import Float
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.knowledge.topics import AREAS
from services.search.vector import cosine_distance
from utils.db.models import Challenge, Innovation, KnowledgeStatus, PowiatFigure

from .schemas import LocalChallenge, LocalFact

REGION = "wojewodztwo-malopolskie"
FIGURES_LIMIT = 6
CHALLENGES_LIMIT = 2
MIN_SCORE = 0.6
SUMMARY_LIMIT = 400


@dataclass(slots=True)
class LocalData:
    facts: list[LocalFact] = field(default_factory=list)
    challenges: list[LocalChallenge] = field(default_factory=list)

    def text(self) -> str:
        lines: list[str] = []
        if self.facts:
            lines.append("Dane z raportów ROPS dla tego powiatu:")
            lines.extend(f"- {fact.sentence()}" for fact in self.facts)
        if self.challenges:
            lines.append("Wyzwania regionalne z dokumentów ROPS bliskie tej innowacji:")
            lines.extend(
                f"- {c.title} ({c.area}): {c.summary} Źródło: {c.source_title}."
                for c in self.challenges
            )
        return "\n".join(lines)


def to_fact(figure: PowiatFigure, region: PowiatFigure | None) -> LocalFact:
    return LocalFact(
        label=figure.label,
        value=figure.value,
        unit=figure.unit,
        year=figure.year,
        region_value=region.value if region else None,
        source_title=figure.source_title,
        source_url=figure.source_url,
        page=figure.page,
    )


async def powiat_facts(session: AsyncSession, powiat: str) -> list[LocalFact]:
    rows = (
        await session.exec(
            select(PowiatFigure)
            .where(col(PowiatFigure.powiat).in_([powiat, REGION]))
            .order_by(col(PowiatFigure.year).desc(), col(PowiatFigure.key))
        )
    ).all()
    region = {(r.key, r.year): r for r in rows if r.powiat == REGION}
    local = [r for r in rows if r.powiat == powiat]
    return [to_fact(r, region.get((r.key, r.year))) for r in local][:FIGURES_LIMIT]


async def near_challenges(
    session: AsyncSession, innovation: Innovation
) -> list[LocalChallenge]:
    if innovation.embedding is None:
        return []
    distance = cosine_distance(Challenge.embedding, list(innovation.embedding))
    score = (1 - distance).cast(Float)
    rows = (
        await session.exec(
            select(Challenge, score)
            .where(
                col(Challenge.status) == KnowledgeStatus.PUBLISHED,
                col(Challenge.embedding).is_not(None),
            )
            .order_by(distance)
            .limit(CHALLENGES_LIMIT)
        )
    ).all()
    return [
        LocalChallenge(
            slug=challenge.slug,
            title=challenge.title,
            area=AREAS.get(challenge.area, challenge.area),
            summary=" ".join(challenge.summary.split())[:SUMMARY_LIMIT],
            source_title=challenge.source_title,
            source_url=challenge.source_url,
            pages=list(challenge.source_pages),
        )
        for challenge, value in rows
        if float(value) >= MIN_SCORE
    ]


async def local_data(
    session: AsyncSession, powiat: str | None, innovation: Innovation
) -> LocalData:
    facts = await powiat_facts(session, powiat) if powiat else []
    return LocalData(facts=facts, challenges=await near_challenges(session, innovation))
