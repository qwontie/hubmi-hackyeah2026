import asyncio
import re
from dataclasses import dataclass
from enum import StrEnum

import httpx

from utils.env import MailSettings
from utils.logging import logger

RESEND_URL = "https://api.resend.com/emails"
TOKEN_IN_LINK = re.compile(r"#token=\S+")
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
ATTEMPTS = 3


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Email:
    to: str
    subject: str
    text: str
    html: str
    reply_to: str | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class Delivery:
    status: DeliveryStatus
    provider_id: str | None = None
    error: str | None = None


def mask_address(address: str) -> str:
    local, _, domain = address.partition("@")
    return f"{local[:1]}***@{domain}" if domain else "***"


class Mailer:
    def __init__(self, settings: MailSettings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    @property
    def enabled(self) -> bool:
        return bool(self._settings.resend_api_key.get_secret_value())

    async def send(self, email: Email) -> Delivery:
        if not self.enabled:
            logger.info(
                "mail skipped, no RESEND key: to=%s subject=%r\n%s",
                mask_address(email.to),
                email.subject,
                TOKEN_IN_LINK.sub("#token=***", email.text),
            )
            return Delivery(DeliveryStatus.SKIPPED)
        payload: dict[str, object] = {
            "from": self._settings.sender,
            "to": [email.to],
            "subject": email.subject,
            "text": email.text,
            "html": email.html,
        }
        reply_to = email.reply_to or self._settings.reply_to
        if reply_to:
            payload["reply_to"] = reply_to
        key = self._settings.resend_api_key.get_secret_value()
        headers = {"Authorization": f"Bearer {key}"}
        if email.idempotency_key:
            headers["Idempotency-Key"] = email.idempotency_key
        return await self._post(payload, headers, email)

    async def _post(
        self, payload: dict[str, object], headers: dict[str, str], email: Email
    ) -> Delivery:
        error = "unknown"
        for attempt in range(ATTEMPTS):
            if attempt:
                await asyncio.sleep(2**attempt)
            try:
                response = await self._client.post(
                    RESEND_URL,
                    json=payload,
                    headers=headers,
                    timeout=self._settings.timeout_seconds,
                )
            except httpx.HTTPError as exc:
                error = f"{type(exc).__name__}: {exc}"
                continue
            if response.is_success:
                provider_id = response.json().get("id")
                logger.info(
                    "mail sent: to=%s subject=%r id=%s",
                    mask_address(email.to),
                    email.subject,
                    provider_id,
                )
                return Delivery(DeliveryStatus.SENT, provider_id=provider_id)
            error = f"{response.status_code}: {response.text[:300]}"
            if response.status_code not in RETRY_STATUSES:
                break
        logger.warning(
            "mail failed: to=%s subject=%r error=%s",
            mask_address(email.to),
            email.subject,
            error,
        )
        return Delivery(DeliveryStatus.FAILED, error=error)
