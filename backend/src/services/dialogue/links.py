import base64
import hashlib
import hmac
import uuid

from utils.env import env

LINK_CONTEXT = b"need-thread:"
LINK_TOKEN_LENGTH = 32


def _base() -> str:
    return env.mailer.public_url.rstrip("/")


def link_token(need_id: uuid.UUID) -> str | None:
    secret = env.auth.secret.get_secret_value()
    if not secret:
        return None
    digest = hmac.new(
        secret.encode(), LINK_CONTEXT + str(need_id).encode(), hashlib.sha256
    ).digest()
    return base64.urlsafe_b64encode(digest).decode()[:LINK_TOKEN_LENGTH]


def link_token_matches(need_id: uuid.UUID, token: str) -> bool:
    expected = link_token(need_id)
    return expected is not None and hmac.compare_digest(expected, token)


def thread_url(need_id: uuid.UUID) -> str:
    url = f"{_base()}/zgloszenie/{need_id}"
    token = link_token(need_id)
    return f"{url}#token={token}" if token else url


def inbox_url() -> str:
    return f"{_base()}/admin/needs"


def admin_need_url(need_id: uuid.UUID | str) -> str:
    return f"{inbox_url()}/{need_id}"


def admin_idea_url(idea_id: uuid.UUID | str) -> str:
    return f"{_base()}/admin/ideas/{idea_id}"
