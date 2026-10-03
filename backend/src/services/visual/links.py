import uuid

from services.signing import key_matches, signed_key

MAX_GENERATIONS = 3
CONTEXT = "idea-visual"


def image_key(idea_id: uuid.UUID, version: int) -> str:
    return signed_key(CONTEXT, idea_id, version)


def image_key_matches(idea_id: uuid.UUID, version: int, key: str | None) -> bool:
    return key_matches(key, CONTEXT, idea_id, version)


def image_url(idea_id: uuid.UUID, version: int | None) -> str | None:
    if version is None:
        return None
    key = image_key(idea_id, version)
    return f"/api/ideas/{idea_id}/visualisation.png?v={version}&key={key}"


def generations_left(used: int) -> int:
    return max(0, MAX_GENERATIONS - used)
