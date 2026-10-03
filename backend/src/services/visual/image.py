import time
from dataclasses import dataclass

from google.genai import types

from services.ai import AiUnavailableError, ensure_budget, log_ai_call
from services.ai.models import google_provider

IMAGE_MODEL = "gemini-3.1-flash-image"
ASPECT_RATIO = "4:3"
IMAGE_SIZE = "1K"
ALLOWED_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})


@dataclass(frozen=True, slots=True)
class Picture:
    data: bytes
    mime_type: str
    model: str


def first_picture(response: types.GenerateContentResponse) -> Picture | None:
    for candidate in response.candidates or []:
        parts = candidate.content.parts if candidate.content else None
        for part in parts or []:
            blob = part.inline_data
            if blob and blob.data and blob.mime_type in ALLOWED_TYPES:
                return Picture(blob.data, blob.mime_type, IMAGE_MODEL)
    return None


async def draw(prompt: str) -> Picture:
    await ensure_budget()
    started = time.perf_counter()
    error: str | None = None
    picture: Picture | None = None
    usage: types.GenerateContentResponseUsageMetadata | None = None
    try:
        response = await google_provider().client.aio.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=ASPECT_RATIO, image_size=IMAGE_SIZE
                ),
            ),
        )
        usage = response.usage_metadata
        picture = first_picture(response)
        if picture is None:
            error = "no image in response"
    except Exception as e:
        error = repr(e)
    await log_ai_call(
        kind="idea_visual_image",
        model=IMAGE_MODEL,
        input_tokens=(usage.prompt_token_count or 0) if usage else 0,
        output_tokens=(usage.candidates_token_count or 0) if usage else 0,
        latency_ms=int((time.perf_counter() - started) * 1000),
        ok=picture is not None,
        error=error,
    )
    if picture is None:
        raise AiUnavailableError(error)
    return picture
