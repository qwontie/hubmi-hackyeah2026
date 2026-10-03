import json
import logging
import time
from collections.abc import Sequence

from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.ai import AiBudgetExceededError, AiUnavailableError, embed_documents
from services.ai.embeddings import cosine, normalize
from utils.db.models.innovation import Innovation, InnovationStatus

logger = logging.getLogger(__name__)

DESCRIPTIONS = {
    "dla-cudzoziemcow": (
        "Cudzoziemcy, migranci i uchodźcy w Polsce: język polski, integracja, "
        "kultura, urzędy dla obcokrajowców."
    ),
    "dla-dzieci-mlodziezy-i-rodziny": (
        "Dzieci, młodzież i rodzina: szkoła, wychowanie, rodzice, piecza zastępcza, "
        "przemoc w rodzinie, kryzys psychiczny młodzieży."
    ),
    "dla-osob-o-ograniczonej-mobilnosci": (
        "Osoby z niepełnosprawnością ruchową: wózek inwalidzki, bariery "
        "architektoniczne, dojazd, transport, poruszanie się, protezy."
    ),
    "dla-osob-w-kryzysie-bezdomnosci": (
        "Bezdomność i ubóstwo: brak mieszkania, utrata domu, noclegownia, higiena, "
        "wychodzenie z bezdomności."
    ),
    "dla-osob-z-niepelnosprawnoscia-intelektualna": (
        "Osoby z niepełnosprawnością intelektualną i autyzmem: samodzielność, "
        "komunikacja, włączenie społeczne."
    ),
    "dla-osob-z-niepelnosprawnoscia-sensoryczna": (
        "Osoby niewidome, słabowidzące, głuche i niedosłyszące: wzrok, słuch, język "
        "migowy, dostępność informacji."
    ),
    "dla-rynku-pracy": (
        "Praca i bezrobocie: utrata pracy, szukanie zatrudnienia, aktywizacja "
        "zawodowa, wypalenie zawodowe."
    ),
    "dla-seniorow": (
        "Seniorzy i osoby starsze: samotność w starszym wieku, demencja, opieka nad "
        "starszym rodzicem, wykluczenie cyfrowe seniorów."
    ),
    "dla-zdrowia-i-medycyny": (
        "Zdrowie i choroby: leczenie, szpital, leki, zdrowie psychiczne dorosłych, "
        "depresja, choroby przewlekłe i onkologiczne."
    ),
}
CENTROID_TTL = 10 * 60

_descriptions: dict[str, list[float]] = {}
_centroids: tuple[float, dict[str, list[float]]] | None = None


def _vector(value: str | Sequence[float]) -> list[float]:
    numbers = json.loads(value) if isinstance(value, str) else value
    return normalize([float(x) for x in numbers])


async def _description_vectors() -> dict[str, list[float]]:
    if not _descriptions:
        slugs = list(DESCRIPTIONS)
        try:
            vectors = await embed_documents(
                [DESCRIPTIONS[s] for s in slugs], kind="embed_category"
            )
        except (AiUnavailableError, AiBudgetExceededError):
            logger.warning("category descriptions not embedded, centroids only")
            return {}
        _descriptions.update(zip(slugs, vectors, strict=True))
    return _descriptions


async def _centroid_vectors(session: AsyncSession) -> dict[str, list[float]]:
    global _centroids  # noqa: PLW0603
    if _centroids is not None and time.monotonic() - _centroids[0] < CENTROID_TTL:
        return _centroids[1]
    rows = (
        await session.exec(
            select(Innovation.category_slug, func.avg(Innovation.embedding))
            .where(
                col(Innovation.status) == InnovationStatus.PUBLISHED,
                col(Innovation.embedding).is_not(None),
            )
            .group_by(col(Innovation.category_slug))
        )
    ).all()
    centroids = {slug: _vector(avg) for slug, avg in rows if slug and avg is not None}
    _centroids = (time.monotonic(), centroids)
    return centroids


async def category_for(session: AsyncSession, vector: list[float] | None) -> str | None:
    if vector is None:
        return None
    centroids = await _centroid_vectors(session)
    if not centroids:
        return None
    descriptions = await _description_vectors()
    query = normalize(vector)

    def score(slug: str) -> float:
        total = cosine(query, centroids[slug])
        if slug in descriptions:
            total += cosine(query, descriptions[slug])
        return total

    return max(centroids, key=score)
