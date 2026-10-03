from urllib.parse import urlsplit

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from api.errors import STATUS_MESSAGES, body
from utils.env import env, is_prod

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
PROTECTED_PREFIXES = ("/api/auth", "/api/admin", "/api/expert")


def _origin(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}".lower()


def _expected_origin(request: Request) -> str:
    if is_prod():
        return _origin(env.mailer.public_url) or ""
    proto = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0]
    host = request.headers.get("x-forwarded-host", request.headers.get("host", ""))
    return f"{proto.strip()}://{host.strip()}".lower()


class SameOriginMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method in UNSAFE_METHODS and request.url.path.startswith(
            PROTECTED_PREFIXES
        ):
            supplied = _origin(request.headers.get("origin")) or _origin(
                request.headers.get("referer")
            )
            if supplied != _expected_origin(request):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content=body("forbidden", STATUS_MESSAGES[403]),
                )
        return await call_next(request)
