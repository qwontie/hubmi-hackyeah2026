from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from utils.logging import logger

STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    503: "unavailable",
}
STATUS_MESSAGES = {
    400: "Nieprawidłowe zapytanie.",
    401: "Zaloguj się, aby kontynuować.",
    403: "Brak uprawnień do tej operacji.",
    404: "Nie znaleziono.",
    405: "Ta operacja nie jest dostępna.",
    409: "Tej operacji nie można teraz wykonać. Odśwież stronę i spróbuj ponownie.",
    422: "Popraw zaznaczone pola.",
    429: "Zbyt wiele prób. Spróbuj ponownie za chwilę.",
    503: "Usługa jest chwilowo niedostępna.",
}
KNOWN_DETAILS = {
    "Not signed in": "Zaloguj się, aby kontynuować.",
    "Wrong login or password": "Nieprawidłowy login lub hasło.",
    "Not Found": "Nie znaleziono.",
    "Method Not Allowed": "Ta operacja nie jest dostępna.",
}
FIELD_MESSAGES = {
    "missing": "To pole jest wymagane.",
    "string_too_short": "Za krótki tekst.",
    "string_too_long": "Za długi tekst.",
    "too_long": "Za dużo elementów.",
    "too_short": "Za mało elementów.",
    "uuid_parsing": "Nieprawidłowy identyfikator.",
    "uuid_type": "Nieprawidłowy identyfikator.",
    "enum": "Niedozwolona wartość.",
    "literal_error": "Niedozwolona wartość.",
    "int_parsing": "Podaj liczbę całkowitą.",
    "greater_than_equal": "Za mała wartość.",
    "less_than_equal": "Za duża wartość.",
    "bool_parsing": "Podaj tak albo nie.",
    "value_error": "Nieprawidłowa wartość.",
    "extra_forbidden": "Nieznane pole.",
}
INTERNAL_MESSAGE = "Wystąpił błąd serwera. Spróbuj ponownie później."


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: Sequence[Mapping[str, str]] | None = None,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = [dict(field) for field in fields] if fields else None
        self.headers = dict(headers) if headers else None


def not_found(message: str = "Nie znaleziono.") -> ApiError:
    return ApiError(status.HTTP_404_NOT_FOUND, "not_found", message)


def conflict(message: str) -> ApiError:
    return ApiError(status.HTTP_409_CONFLICT, "conflict", message)


def invalid(field: str, message: str) -> ApiError:
    return ApiError(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "validation_error",
        STATUS_MESSAGES[422],
        fields=[{"field": field, "message": message}],
    )


def body(
    code: str, message: str, fields: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    detail: dict[str, Any] = {"code": code, "message": message}
    if fields:
        detail["fields"] = fields
    return {"detail": detail}


async def api_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    return JSONResponse(
        body(exc.code, exc.message, exc.fields),
        status_code=exc.status_code,
        headers=exc.headers,
    )


async def http_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    code = STATUS_CODES.get(exc.status_code, "error")
    detail = exc.detail if isinstance(exc.detail, str) else ""
    message = KNOWN_DETAILS.get(detail) or STATUS_MESSAGES.get(
        exc.status_code, INTERNAL_MESSAGE
    )
    return JSONResponse(
        body(code, message), status_code=exc.status_code, headers=exc.headers
    )


def field_name(location: Sequence[Any]) -> str:
    parts = [str(part) for part in location[1:]] or [str(part) for part in location]
    return ".".join(parts)


async def validation_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = exc.errors()
    if any(error.get("loc", ("",))[0] == "path" for error in errors):
        return JSONResponse(
            body("not_found", STATUS_MESSAGES[404]),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if any(error.get("type") == "json_invalid" for error in errors):
        return JSONResponse(
            body("bad_request", STATUS_MESSAGES[400]),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    fields = [
        {
            "field": field_name(error.get("loc", ())),
            "message": FIELD_MESSAGES.get(
                str(error.get("type", "")), "Nieprawidłowa wartość."
            ),
        }
        for error in errors
    ]
    return JSONResponse(
        body("validation_error", STATUS_MESSAGES[422], fields),
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled error on %s %s", request.method, request.url.path, exc_info=exc
    )
    return JSONResponse(
        body("internal", INTERNAL_MESSAGE),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def install(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)
