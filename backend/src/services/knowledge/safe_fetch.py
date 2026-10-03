import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

import httpx

from services.ingest.fetch import USER_AGENT

ALLOWED_SCHEMES = frozenset({"http", "https"})
ALLOWED_PORTS = frozenset({None, 80, 443})


class BlockedUrlError(ValueError):
    pass


async def check_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.hostname:
        message = "only http and https links"
        raise BlockedUrlError(message)
    if parsed.port not in ALLOWED_PORTS:
        message = "only standard ports"
        raise BlockedUrlError(message)
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(
            parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM
        )
    except OSError as e:
        message = "unknown host"
        raise BlockedUrlError(message) from e
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            message = "address is not public"
            raise BlockedUrlError(message)


async def _guard(request: httpx.Request) -> None:
    await check_url(str(request.url))


def public_client(timeout: float = 30.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT, "Accept-Language": "pl"},
        timeout=httpx.Timeout(timeout),
        follow_redirects=True,
        max_redirects=5,
        event_hooks={"request": [_guard]},
    )


async def fetch_limited(
    client: httpx.AsyncClient, url: str, limit: int
) -> tuple[bytes, str]:
    async with client.stream("GET", url) as response:
        response.raise_for_status()
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > limit:
                message = f"larger than {limit} bytes"
                raise BlockedUrlError(message)
            chunks.append(chunk)
        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        return b"".join(chunks), content_type.lower()
