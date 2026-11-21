"""Parse token responses without decoding JWT claims or exposing credentials."""

import json
import math
import re

from fitro_mcp.errors import BridgeError

_COMPACT_JWT = re.compile(rb"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_BEARER_TOKEN = re.compile(r"[A-Za-z0-9._~+/-]+=*")


def parse_token_response(body: bytes) -> tuple[str, float]:
    """Accept observed raw JWTs and compatible JSON envelopes; return private values.

    Token values must remain in memory and must never be logged or returned as MCP
    data. JWT syntax recognition does not verify or trust its claims. Authentication
    relies on the verified upstream HTTPS exchange, followed by the API bearer check.
    """
    try:
        try:
            data = json.loads(body)
        except (ValueError, UnicodeError):
            raw = body.strip()
            if _COMPACT_JWT.fullmatch(raw) is None:
                raise ValueError from None
            data = raw.decode("ascii")
        token: object
        if isinstance(data, str):
            token = data
            lifetime = 86400.0
        elif isinstance(data, dict):
            token = data.get("access_token", data.get("accessToken"))
            expires = data.get("expires_in", data.get("expiresIn", 86400))
            if isinstance(expires, bool) or not isinstance(expires, (int, float, str)):
                raise ValueError
            lifetime = float(expires)
        else:
            raise ValueError
        if (
            not isinstance(token, str)
            or _BEARER_TOKEN.fullmatch(token) is None
            or not math.isfinite(lifetime)
            or lifetime <= 0
        ):
            raise ValueError
    except (ValueError, TypeError, OverflowError):
        raise BridgeError("Unsupported token response. See docs/authentication.md.") from None
    return token, lifetime
