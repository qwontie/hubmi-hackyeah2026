import hmac
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlmodel import col
from sqlmodel import select as entity_select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.needs import hash_token
from services.needs.tokens import new_token
from services.signing import key_matches, signed_key
from utils.db.models import ApplicationStatus, GrantApplication, GrantCall, Idea

from .calls import ref, sections_of
from .drafting import Draft, draft_sections
from .schemas import (
    AdminApplication,
    AdminApplicationSummary,
    ApplicationOut,
    ApplicationSection,
    GrantSection,
    IdeaRef,
    SectionSource,
)

PDF_CONTEXT = "application-pdf"
SOURCES: frozenset[str] = frozenset({"idea", "ai", "author"})
IDEA_FIELDS: dict[str, str] = {
    "title": "title",
    "description": "essence",
    "recipients": "for_whom",
}
CANVAS_FIELDS: dict[str, str] = {
    "diagnosis": "problem",
    "novelty": "novelty",
    "testing": "micro_test",
    "change": "measures",
    "team": "partners",
    "preparation": "resources",
}


class NothingToDraftError(ValueError):
    pass


class SectionError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def unknown_section(field: str) -> SectionError:
    return SectionError(field, "Nie ma takiej sekcji w naborze.")


def too_long(field: str, limit: int) -> SectionError:
    return SectionError(field, f"Najwyżej {limit} znaków.")


def pdf_key(application_id: uuid.UUID) -> str:
    return signed_key(PDF_CONTEXT, application_id)


def pdf_key_matches(application_id: uuid.UUID, key: str | None) -> bool:
    return key_matches(key, PDF_CONTEXT, application_id)


def stored(application: GrantApplication, key: str) -> dict[str, Any]:
    raw = application.sections.get(key)
    return raw if isinstance(raw, dict) else {}


def source_of(raw: dict[str, Any], text: str) -> SectionSource:
    if not text.strip():
        return "empty"
    source = raw.get("source")
    if source == "idea":
        return "idea"
    if source == "author":
        return "author"
    return "ai"


def section_views(
    application: GrantApplication, sections: Sequence[GrantSection]
) -> list[ApplicationSection]:
    views = []
    for section in sections:
        raw = stored(application, section.key)
        text = str(raw.get("text") or "")
        views.append(
            ApplicationSection(
                key=section.key,
                label=section.label,
                hint=section.hint,
                max_length=section.max_length,
                required=section.required,
                text=text,
                missing=[str(item) for item in raw.get("missing") or []],
                source=source_of(raw, text),
            )
        )
    return views


def incomplete(view_: ApplicationSection) -> bool:
    if not view_.text.strip():
        return True
    return view_.source == "ai" and bool(view_.missing)


def missing_required(views: Sequence[ApplicationSection]) -> list[str]:
    return [view_.key for view_ in views if view_.required and incomplete(view_)]


def idea_ref(idea: Idea) -> IdeaRef:
    return IdeaRef(id=idea.id, number=idea.number or 0, title=idea.title)


def token_opens_application(application: GrantApplication, token: str | None) -> bool:
    if not token or application.edit_token_hash is None:
        return False
    return hmac.compare_digest(hash_token(token), application.edit_token_hash)


def issue_token(application: GrantApplication) -> str:
    token, token_hash = new_token()
    application.edit_token_hash = token_hash
    return token


def set_contact(
    application: GrantApplication, *, email: str | None, consent: bool | None
) -> None:
    if consent is False or (email is not None and not email):
        application.contact_email = None
        application.contact_consent = False
    elif email:
        application.contact_email = email
        application.contact_consent = True


def view(
    application: GrantApplication, call: GrantCall, idea: Idea | None
) -> ApplicationOut:
    views = section_views(application, sections_of(call))
    return ApplicationOut(
        id=application.id,
        number=application.number or 0,
        call=ref(call),
        idea=idea_ref(idea) if idea else None,
        contact_email=application.contact_email,
        contact_consent=application.contact_consent,
        status=application.status,
        sections=views,
        missing_required=missing_required(views),
        pdf_url=(
            f"/api/applications/{application.id}/export.pdf"
            f"?key={pdf_key(application.id)}"
        ),
        submitted_at=application.submitted_at,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


async def load(
    session: AsyncSession, application_id: uuid.UUID
) -> tuple[GrantApplication, GrantCall, Idea | None] | None:
    application = await session.get(GrantApplication, application_id)
    if application is None:
        return None
    call = await session.get(GrantCall, application.call_id)
    if call is None:
        return None
    idea = await session.get(Idea, application.idea_id) if application.idea_id else None
    if application.idea_id is not None and idea is None:
        return None
    return application, call, idea


async def find(
    session: AsyncSession, call_id: uuid.UUID, idea_id: uuid.UUID
) -> GrantApplication | None:
    rows = await session.exec(
        entity_select(GrantApplication).where(
            col(GrantApplication.call_id) == call_id,
            col(GrantApplication.idea_id) == idea_id,
        )
    )
    return rows.first()


def apply_draft(
    application: GrantApplication, draft: Draft, keys: set[str] | None
) -> None:
    sections = dict(application.sections)
    for item in draft.sections:
        if keys is not None and item.key not in keys:
            continue
        if stored(application, item.key).get("source") == "author":
            continue
        sections[item.key] = {
            "text": item.text,
            "missing": item.missing,
            "source": "ai",
        }
    application.sections = sections


def idea_copy(idea: Idea, sections: Sequence[GrantSection]) -> dict[str, Any]:
    canvas = idea.canvas or {}
    copied: dict[str, Any] = {}
    for section in sections:
        if section.key in IDEA_FIELDS:
            value = getattr(idea, IDEA_FIELDS[section.key])
        else:
            value = canvas.get(CANVAS_FIELDS.get(section.key, section.key))
        text = " ".join(str(value or "").split())[: section.max_length]
        if text:
            copied[section.key] = {"text": text, "missing": [], "source": "idea"}
    return copied


def author_answers(
    application: GrantApplication, sections: Sequence[GrantSection]
) -> str:
    lines = []
    for section in sections:
        text = str(stored(application, section.key).get("text") or "").strip()
        if text:
            lines.append(f"{section.label}: {text}")
    return "\n".join(lines)


async def start(
    session: AsyncSession, call: GrantCall, idea: Idea | None
) -> tuple[GrantApplication, str, bool]:
    if idea is not None:
        existing = await find(session, call.id, idea.id)
        if existing is not None:
            token = issue_token(existing)
            session.add(existing)
            await session.commit()
            await session.refresh(existing)
            return existing, token, False
    application = GrantApplication(
        call_id=call.id,
        idea_id=idea.id if idea else None,
        sections=idea_copy(idea, sections_of(call)) if idea else {},
    )
    token = issue_token(application)
    session.add(application)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await find(session, call.id, idea.id) if idea else None
        if existing is None:
            raise
        token = issue_token(existing)
        session.add(existing)
        await session.commit()
        await session.refresh(existing)
        return existing, token, False
    await session.refresh(application)
    return application, token, True


async def suggest(
    session: AsyncSession,
    application: GrantApplication,
    call: GrantCall,
    idea: Idea | None,
    keys: Sequence[str] | None,
) -> GrantApplication:
    sections = sections_of(call)
    known = {s.key for s in sections}
    wanted = set(keys) if keys else None
    if wanted is not None:
        unknown = sorted(wanted - known)
        if unknown:
            error = unknown_section(f"keys.{unknown[0]}")
            raise error
    answers = author_answers(application, sections)
    if idea is None and not answers:
        raise NothingToDraftError
    await session.commit()
    draft, model = await draft_sections(call, sections, idea, answers)
    apply_draft(application, draft, wanted)
    application.model = model
    session.add(application)
    await session.commit()
    await session.refresh(application)
    return application


def edit_sections(
    application: GrantApplication, call: GrantCall, changes: dict[str, str]
) -> None:
    sections = {s.key: s for s in sections_of(call)}
    updated = dict(application.sections)
    for key, value in changes.items():
        section = sections.get(key)
        if section is None:
            error = unknown_section(f"sections.{key}")
            raise error
        text = value.strip()
        if len(text) > section.max_length:
            error = too_long(f"sections.{key}", section.max_length)
            raise error
        previous = stored(application, key)
        updated[key] = {
            "text": text,
            "missing": previous.get("missing") or [],
            "source": "author",
        }
    application.sections = updated


def submit_errors(application: GrantApplication, call: GrantCall) -> list[dict]:
    errors = []
    for view_ in section_views(application, sections_of(call)):
        if view_.required and incomplete(view_):
            errors.append(
                {"field": f"sections.{view_.key}", "message": "Uzupełnij tę sekcję."}
            )
        elif len(view_.text) > view_.max_length:
            errors.append(
                {
                    "field": f"sections.{view_.key}",
                    "message": f"Najwyżej {view_.max_length} znaków.",
                }
            )
    return errors


def mark_submitted(application: GrantApplication) -> None:
    application.status = ApplicationStatus.SUBMITTED
    application.submitted_at = datetime.now(UTC)


def summary(
    application: GrantApplication, call: GrantCall, idea: Idea | None
) -> AdminApplicationSummary:
    views = section_views(application, sections_of(call))
    return AdminApplicationSummary(
        id=application.id,
        number=application.number or 0,
        call_id=call.id,
        idea=idea_ref(idea) if idea else None,
        status=application.status,
        missing_required=missing_required(views),
        submitted_at=application.submitted_at,
        updated_at=application.updated_at,
    )


def admin_view(
    application: GrantApplication, call: GrantCall, idea: Idea | None
) -> AdminApplication:
    return AdminApplication(
        **view(application, call, idea).model_dump(),
        idea_contact=bool(idea and idea.contact_email and idea.contact_consent),
    )


async def list_for_call(
    session: AsyncSession,
    call: GrantCall,
    status: ApplicationStatus | None,
    page: int,
    per_page: int,
) -> tuple[list[AdminApplicationSummary], int]:
    filters = [col(GrantApplication.call_id) == call.id]
    if status is not None:
        filters.append(col(GrantApplication.status) == status)
    total = await session.scalar(
        select(func.count()).select_from(GrantApplication).where(*filters)
    )
    rows = await session.exec(
        entity_select(GrantApplication, Idea)
        .outerjoin(Idea, col(Idea.id) == col(GrantApplication.idea_id))
        .where(*filters)
        .order_by(
            col(GrantApplication.submitted_at).desc().nulls_last(),
            col(GrantApplication.updated_at).desc(),
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return [summary(a, call, idea) for a, idea in rows.all()], int(total or 0)
