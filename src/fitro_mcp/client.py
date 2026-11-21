"""Bounded async HTTP and in-memory API-key to bearer-token authentication."""

import asyncio
import json
import logging
import time
from typing import Any

import httpx

from fitro_mcp.authentication import parse_token_response
from fitro_mcp.catalog import Operation
from fitro_mcp.config import Settings
from fitro_mcp.diagnostics import event
from fitro_mcp.errors import BridgeError

TOKEN_PATH = "/personalapitoken-service/personal-api/personal-api-key/token"  # noqa: S105


class PersonalAPIClient:
    """Own one connection pool and a synchronized, memory-only token cache.

    Construct per server lifespan and always close with ``aclose``. Production
    origins come exclusively from Settings; transport injection is for isolated
    tests. Public operations never accept raw URLs or arbitrary HTTP methods.
    """

    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None):
        """Accept a transport for isolated tests; upstream origins remain fixed."""
        self._settings = settings
        self._http = httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def aclose(self) -> None:
        """Discard the cached token and close all connections."""
        self._token = None
        self._expires_at = 0
        await self._http.aclose()

    async def _request(
        self, method: str, path: str, authorization: str, *, params: dict[str, Any] | None = None
    ) -> tuple[int, bytes]:
        """Stream a bounded body, returning status separately from safe error handling.

        Error bodies are intentionally ignored. Successful token responses have a
        64 KiB cap in addition to the configured data-response limit. The diagnostic
        duration measures response-header latency; no path or body is logged.
        """
        started = time.monotonic()
        try:
            async with self._http.stream(
                method, path, headers={"Authorization": authorization}, params=params
            ) as response:
                event(
                    "http_completed",
                    status=response.status_code,
                    duration_ms=int((time.monotonic() - started) * 1000),
                    level=logging.WARNING if response.status_code >= 400 else logging.DEBUG,
                )
                # Never read error bodies: they can contain credentials and health data.
                if not 200 <= response.status_code < 300:
                    return response.status_code, b""
                limit = (
                    min(self._settings.max_response_bytes, 65536)
                    if method == "POST"
                    else (self._settings.max_response_bytes)
                )
                content = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    if len(content) + len(chunk) > limit:
                        raise BridgeError(
                            "Response exceeds configured size limit. Narrow the query."
                        )
                    content.extend(chunk)
                return response.status_code, bytes(content)
        except httpx.HTTPError:
            event("http_failed", level=logging.WARNING)
            raise BridgeError("Upstream connection failed or timed out. Try again later.") from None

    @staticmethod
    def _check_status(status: int) -> None:
        """Translate upstream status to a fixed message without its response body."""
        if 200 <= status < 300:
            return
        messages = {
            401: "Authentication failed. Check your Personal API key and its expiration.",
            403: "Access denied. Check account permissions and API access.",
            404: "Requested data was not found.",
            429: "Upstream rate limit reached. Wait before trying again.",
        }
        raise BridgeError(messages.get(status, f"Upstream request failed (HTTP {status})."))

    async def _get_token(self, rejected: str | None = None) -> str:
        """Reuse a valid token or exchange the key under a per-client async lock.

        ``rejected`` identifies the bearer that received 401. Another concurrent
        request may already have replaced it; that replacement is reused instead
        of generating another token. Deadlines use the monotonic clock so wall
        clock changes cannot extend a cached credential's lifetime.
        """
        async with self._lock:
            if (
                self._token is not None
                and self._token != rejected
                and time.monotonic() < self._expires_at
            ):
                event("token_cache_hit")
                return self._token
            event("token_exchange")
            status, body = await self._request(
                "POST", TOKEN_PATH, f"ApiKey {self._settings.api_key.get_secret_value()}"
            )
            self._check_status(status)
            token, lifetime = parse_token_response(body)
            self._token = token
            self._expires_at = time.monotonic() + max(0, min(lifetime, 86400) - 60)
            return token

    async def execute(self, operation: Operation, arguments: dict[str, Any]) -> Any:
        """Run one allowlisted GET, renewing once on a rejected bearer token."""
        path, query = operation.prepare(arguments)
        token = await self._get_token()
        status, body = await self._request("GET", path, f"Bearer {token}", params=query)
        if status == 401:
            event("token_renewal")
            token = await self._get_token(rejected=token)
            status, body = await self._request("GET", path, f"Bearer {token}", params=query)
        self._check_status(status)
        if operation.binary:
            return body
        try:
            return json.loads(body)
        except ValueError:
            raise BridgeError("Upstream returned invalid JSON.") from None
