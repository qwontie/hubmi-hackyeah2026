import hashlib

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.ai import embed_documents
from utils.db.models.challenge import Challenge

from .topics import AREAS

MAX_EMBED_CHARS = 4000


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def challenge_text(challenge: Challenge) -> str:
    parts = [
        challenge.title,
        f"Obszar: {AREAS.get(challenge.area, challenge.area)}",
        challenge.summary,
        challenge.description,
    ]
    return "\n\n".join(p for p in parts if p.strip())[:MAX_EMBED_CHARS]


async def refresh_challenge_embeddings(session: AsyncSession) -> int:
    rows = (await session.exec(select(Challenge))).all()
    todo: list[tuple[Challenge, str]] = []
    for row in rows:
        text = challenge_text(row)
        if row.embedding is None or row.embedded_hash != text_hash(text):
            todo.append((row, text))
    if not todo:
        return 0
    vectors = await embed_documents([t for _, t in todo], kind="embed_challenge")
    for (row, text), vector in zip(todo, vectors, strict=True):
        row.embedding = vector
        row.embedded_hash = text_hash(text)
        session.add(row)
    await session.commit()
    return len(todo)
