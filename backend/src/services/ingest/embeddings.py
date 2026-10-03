import hashlib

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.ai import embed_documents
from utils.db.models.innovation import Innovation

MAX_EMBED_CHARS = 7000


def embedding_text(innovation: Innovation) -> str:
    parts = [
        innovation.title,
        innovation.lead,
        f"Jakich problemów dotyczy: {innovation.problems}",
        f"Grupa docelowa: {innovation.target_group}",
        f"Na czym polega: {innovation.what_it_is}",
        f"Kto może skorzystać: {innovation.who_can_use}",
    ]
    return "\n\n".join(p for p in parts if p.strip())[:MAX_EMBED_CHARS]


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def refresh_embeddings(session: AsyncSession) -> int:
    rows = (await session.exec(select(Innovation))).all()
    todo: list[tuple[Innovation, str]] = []
    for row in rows:
        text = embedding_text(row)
        if row.embedding is None or row.embedded_hash != text_hash(text):
            todo.append((row, text))
    if not todo:
        return 0
    vectors = await embed_documents([t for _, t in todo], kind="embed_innovation")
    for (item, text), vector in zip(todo, vectors, strict=True):
        item.embedding = vector
        item.embedded_hash = text_hash(text)
        session.add(item)
    await session.commit()
    return len(todo)
