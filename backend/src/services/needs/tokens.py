import hashlib
import secrets


def new_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(24)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def token_matches(token: str | None, expected_hash: str) -> bool:
    if not token:
        return False
    return secrets.compare_digest(hash_token(token), expected_hash)
