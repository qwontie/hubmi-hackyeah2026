import base64
import hashlib
import hmac

from utils.env import env

KEY_LENGTH = 24


def signed_key(context: str, *parts: object) -> str:
    secret = env.auth.secret.get_secret_value() or "hubmi-unsigned"
    message = ":".join([context, *(str(part) for part in parts)]).encode()
    digest = hmac.new(secret.encode(), message, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode()[:KEY_LENGTH]


def key_matches(key: str | None, context: str, *parts: object) -> bool:
    if not key:
        return False
    return hmac.compare_digest(signed_key(context, *parts), key)
