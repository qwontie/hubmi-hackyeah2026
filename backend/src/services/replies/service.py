from datetime import UTC, datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from services.needs import POWIATS
from utils.db.models import Need
from utils.env import env

from .schemas import Fragment, InnovationRef, ReplySuggestions
from .sources import earlier_answers, matched
from .writer import write

CLOSING = (
    "Pozdrawiamy serdecznie\nZespół Regionalnego Ośrodka Polityki Społecznej w Krakowie"
)


def card_url(slug: str) -> str:
    return f"{env.mailer.public_url.rstrip('/')}/innowacje/{slug}"


def cached(need: Need) -> ReplySuggestions | None:
    if need.reply_suggestions is None:
        return None
    return ReplySuggestions.model_validate(need.reply_suggestions)


async def suggest(
    session: AsyncSession, need: Need, *, refresh: bool = False
) -> ReplySuggestions:
    stored = None if refresh else cached(need)
    if stored is not None:
        return stored
    suggestions = await _generate(session, need)
    need.reply_suggestions = suggestions.model_dump(mode="json")
    session.add(need)
    await session.commit()
    return suggestions


async def _generate(session: AsyncSession, need: Need) -> ReplySuggestions:
    items = await matched(session, need.id)
    earlier = await earlier_answers(session, need)
    powiat = POWIATS.get(need.powiat) if need.powiat else None
    draft = await write(need, powiat, items)
    texts = {part.slug: part.text for part in draft.innovations}
    fragments = [
        Fragment(id="opening", kind="opening", label="Powitanie", text=draft.opening)
    ]
    for item in items:
        innovation = item.innovation
        body = texts.get(innovation.slug)
        if not body:
            continue
        url = card_url(innovation.slug)
        fragments.append(
            Fragment(
                id=f"innovation:{innovation.slug}",
                kind="innovation",
                label=innovation.title,
                text=f"{body} Więcej: {url}",
                innovation=InnovationRef(
                    slug=innovation.slug, title=innovation.title, url=url
                ),
            )
        )
    fragments.append(
        Fragment(
            id="next_step", kind="next_step", label="Co dalej", text=draft.next_step
        )
    )
    fragments.append(
        Fragment(id="closing", kind="closing", label="Pożegnanie", text=CLOSING)
    )
    return ReplySuggestions(
        fragments=fragments, earlier_answers=earlier, generated_at=datetime.now(UTC)
    )
