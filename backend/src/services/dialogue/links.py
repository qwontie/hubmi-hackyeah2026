import base64
import hashlib
import hmac
import uuid

from utils.env import env

NEED_CONTEXT = b"need-thread:"
IDEA_CONTEXT = b"idea-thread:"
LINK_TOKEN_LENGTH = 32


def _base() -> str:
    return env.mailer.public_url.rstrip("/")


def link_token(owner_id: uuid.UUID, context: bytes = NEED_CONTEXT) -> str | None:
    secret = env.auth.secret.get_secret_value()
    if not secret:
        return None
    digest = hmac.new(
        secret.encode(), context + str(owner_id).encode(), hashlib.sha256
    ).digest()
    return base64.urlsafe_b64encode(digest).decode()[:LINK_TOKEN_LENGTH]


def link_token_matches(
    owner_id: uuid.UUID, token: str, context: bytes = NEED_CONTEXT
) -> bool:
    expected = link_token(owner_id, context)
    return expected is not None and hmac.compare_digest(expected, token)


def _with_token(url: str, token: str | None) -> str:
    return f"{url}#token={token}" if token else url


def thread_url(need_id: uuid.UUID) -> str:
    return _with_token(f"{_base()}/zgloszenie/{need_id}", link_token(need_id))


def idea_thread_url(idea_id: uuid.UUID) -> str:
    return _with_token(f"{_base()}/pomysl/{idea_id}", link_token(idea_id, IDEA_CONTEXT))


def inbox_url() -> str:
    return f"{_base()}/admin/needs"


def admin_need_url(need_id: uuid.UUID | str) -> str:
    return f"{inbox_url()}/{need_id}"


def admin_idea_url(idea_id: uuid.UUID | str) -> str:
    return f"{_base()}/admin/ideas/{idea_id}"
