import hashlib
import hmac
import secrets

TOKEN_BYTES = 32


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(TOKEN_BYTES)
    return token, token_hash(token)


def token_matches(expected_hash: str, token: str | None) -> bool:
    return bool(token) and hmac.compare_digest(expected_hash, token_hash(token or ""))
