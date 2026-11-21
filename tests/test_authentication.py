import json

import httpx
import pytest
from test_client import settings

from fitro_mcp.authentication import parse_token_response
from fitro_mcp.catalog import load_catalog
from fitro_mcp.client import TOKEN_PATH, PersonalAPIClient
from fitro_mcp.errors import BridgeError

SYNTHETIC_JWT = "synthetic.payload.signature"


@pytest.mark.parametrize(
    "body,lifetime",
    [
        (SYNTHETIC_JWT.encode(), 86400),
        ((" \n" + SYNTHETIC_JWT + "\r\n").encode(), 86400),
        (json.dumps(SYNTHETIC_JWT).encode(), 86400),
        (json.dumps({"access_token": SYNTHETIC_JWT, "expires_in": 3600}).encode(), 3600),
        (json.dumps({"accessToken": SYNTHETIC_JWT, "expiresIn": "1800"}).encode(), 1800),
    ],
)
def test_supported_formats(body, lifetime):
    assert parse_token_response(body) == (SYNTHETIC_JWT, lifetime)


@pytest.mark.parametrize(
    "body",
    [
        b"",
        b"<html>SECRET upstream page</html>",
        b"SECRET not json",
        b"opaque-raw-value",
        b"synthetic.payload.signature\r\nInjected: SECRET",
        b"\xff\xfe",
        b"null",
        b"[]",
        b"123",
        b'{"access_token":"bad\\r\\nSECRET"}',
        b'{"access_token":""}',
        b'{"access_token":"ok","expires_in":true}',
        b'{"access_token":"ok","expires_in":0}',
        b'{"access_token":"ok","expires_in":-1}',
        b'{"access_token":"ok","expires_in":"Infinity"}',
        b'{"access_token":"ok","expires_in":null}',
        b'{"access_token":"ok","expires_in":1e9999}',
        json.dumps({"access_token": "ok", "expires_in": 10**1000}).encode(),
    ],
)
def test_malformed_responses_fail_without_echoing_credentials(body):
    with pytest.raises(BridgeError) as error:
        parse_token_response(body)
    assert str(error.value) == "Unsupported token response. See docs/authentication.md."


async def test_plain_jwt_exchange_precedes_data_call_and_is_cached():
    requests = []

    def handler(request):
        requests.append(request)
        if request.method == "POST":
            assert request.url.path == TOKEN_PATH
            assert request.headers["authorization"] == "ApiKey test-secret-key"
            return httpx.Response(200, text=SYNTHETIC_JWT)
        assert request.headers["authorization"] == f"Bearer {SYNTHETIC_JWT}"
        return httpx.Response(200, json=[])

    client = PersonalAPIClient(settings(), transport=httpx.MockTransport(handler))
    try:
        for _ in range(2):
            assert await client.execute(load_catalog()["get_activity_types"], {}) == []
        assert [request.method for request in requests] == ["POST", "GET", "GET"]
    finally:
        await client.aclose()


async def test_plain_jwt_renewal_on_401():
    exchanges = 0

    def handler(request):
        nonlocal exchanges
        if request.method == "POST":
            exchanges += 1
            return httpx.Response(200, text=f"synthetic.payload.signature{exchanges}")
        if request.headers["authorization"].endswith("signature1"):
            return httpx.Response(401)
        return httpx.Response(200, json=[])

    client = PersonalAPIClient(settings(), transport=httpx.MockTransport(handler))
    try:
        assert await client.execute(load_catalog()["get_activity_types"], {}) == []
        assert exchanges == 2
    finally:
        await client.aclose()
