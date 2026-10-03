import math
import time
from collections.abc import Sequence
from functools import cache
from typing import Literal

from pydantic_ai import Embedder
from pydantic_ai.embeddings.google import GoogleEmbeddingModel, GoogleEmbeddingSettings

from utils.db.models.innovation import EMBEDDING_DIMENSIONS

from .costs import ensure_budget, log_ai_call
from .models import AiUnavailableError, google_provider

EMBEDDING_MODEL = "gemini-embedding-001"
BATCH_SIZE = 50
CHARS_PER_TOKEN = 3


@cache
def embedder() -> Embedder:
    return Embedder(
        GoogleEmbeddingModel(EMBEDDING_MODEL, provider=google_provider()),
        settings=GoogleEmbeddingSettings(
            dimensions=EMBEDDING_DIMENSIONS, truncate=True
        ),
    )


@cache
def title_embedder() -> Embedder:
    return Embedder(
        GoogleEmbeddingModel(EMBEDDING_MODEL, provider=google_provider()),
        settings=GoogleEmbeddingSettings(
            dimensions=EMBEDDING_DIMENSIONS,
            truncate=True,
            google_task_type="SEMANTIC_SIMILARITY",
        ),
    )


def normalize(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return list(vector)
    return [x / norm for x in vector]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


async def _embed(
    texts: list[str], *, kind: str, mode: Literal["query", "document", "title"]
) -> list[list[float]]:
    await ensure_budget()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        tokens = sum(len(t) for t in batch) // CHARS_PER_TOKEN
        started = time.perf_counter()
        try:
            if mode == "query":
                result = await embedder().embed_query(batch)
            elif mode == "title":
                result = await title_embedder().embed_documents(batch)
            else:
                result = await embedder().embed_documents(batch)
        except Exception as e:
            await log_ai_call(
                kind=kind,
                model=EMBEDDING_MODEL,
                input_tokens=tokens,
                output_tokens=0,
                latency_ms=int((time.perf_counter() - started) * 1000),
                ok=False,
                error=repr(e),
            )
            raise AiUnavailableError from e
        await log_ai_call(
            kind=kind,
            model=EMBEDDING_MODEL,
            input_tokens=result.usage.input_tokens or tokens,
            output_tokens=0,
            latency_ms=int((time.perf_counter() - started) * 1000),
            ok=True,
        )
        vectors.extend(normalize(v) for v in result.embeddings)
    return vectors


async def embed_documents(texts: list[str], *, kind: str) -> list[list[float]]:
    return await _embed(texts, kind=kind, mode="document")


async def embed_queries(texts: list[str], *, kind: str) -> list[list[float]]:
    return await _embed(texts, kind=kind, mode="query")


async def embed_query(text: str, *, kind: str) -> list[float]:
    return (await embed_queries([text], kind=kind))[0]


async def embed_titles(texts: list[str], *, kind: str) -> list[list[float]]:
    return await _embed(texts, kind=kind, mode="title")
