import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from fitro_mcp.catalog import load_catalog
from fitro_mcp.client import PersonalAPIClient
from fitro_mcp.config import Settings
from fitro_mcp.errors import BridgeError

CATALOG = load_catalog()


def settings(**kwargs):
    return Settings(api_key=SecretStr("test-secret-key"), **kwargs)


async def test_auth_cache_concurrency_and_query():
    requests = []

    def handler(request):
        requests.append(request)
        if request.method == "POST":
            assert request.headers["authorization"] == "ApiKey test-secret-key"
            return httpx.Response(200, json={"access_token": "test-bearer", "expires_in": 86400})
        assert request.headers["authorization"] == "Bearer test-bearer"
        assert request.url.params["calendarDate"] == "2026-11-20"
        return httpx.Response(200, json={"steps": 42})

    client = PersonalAPIClient(settings(), transport=httpx.MockTransport(handler))
    results = await asyncio.gather(
        *[
            client.execute(CATALOG["get_daily_summary"], {"calendarDate": "2026-11-20"})
            for _ in range(5)
        ]
    )
    assert results == [{"steps": 42}] * 5
    assert sum(r.method == "POST" for r in requests) == 1
    await client.aclose()
    assert client._token is None


async def test_401_renews_once():
    tokens = 0
    gets = 0

    def handler(request):
        nonlocal tokens, gets
        if request.method == "POST":
            tokens += 1
            return httpx.Response(200, json={"accessToken": f"token-{tokens}"})
        gets += 1
        return httpx.Response(401, text="private upstream data")

    client = PersonalAPIClient(settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(BridgeError, match="Authentication failed"):
        await client.execute(CATALOG["get_activity_types"], {})
    assert (tokens, gets) == (2, 2)
    await client.aclose()


@pytest.mark.parametrize("status", [302, 400, 403, 404, 429, 500])
async def test_error_bodies_are_redacted_and_redirects_not_followed(status):
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            return httpx.Response(200, json={"access_token": "bearer"})
        return httpx.Response(status, text="SECRET", headers={"location": "https://evil.invalid"})

    client = PersonalAPIClient(settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(BridgeError) as error:
        await client.execute(CATALOG["get_activity_types"], {})
    assert "SECRET" not in str(error.value)
    assert len(calls) == 2
    assert all(r.url.host == "personal.connectapi.garmin.com" for r in calls)
    await client.aclose()


@pytest.mark.parametrize(
    "data", [{}, [], {"access_token": "bad\r\nheader"}, {"access_token": "ok", "expires_in": "nan"}]
)
async def test_bad_token_response(data):
    client = PersonalAPIClient(
        settings(), transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data))
    )
    with pytest.raises(BridgeError, match="Unsupported token response"):
        await client.execute(CATALOG["get_activity_types"], {})
    await client.aclose()


async def test_limits_binary_and_invalid_json():
    body = b"zip-bytes"

    def handler(request):
        if request.method == "POST":
            return httpx.Response(200, json={"access_token": "ok"})
        return httpx.Response(200, content=body)

    client = PersonalAPIClient(
        settings(max_response_bytes=1024), transport=httpx.MockTransport(handler)
    )
    assert await client.execute(CATALOG["get_download_activity"], {"activityId": 1}) == body
    with pytest.raises(BridgeError, match="invalid JSON"):
        await client.execute(CATALOG["get_activity_types"], {})
    body = b"x" * 1025
    with pytest.raises(BridgeError, match="size limit"):
        await client.execute(CATALOG["get_activity_types"], {})
    await client.aclose()


async def test_transport_failure():
    def handler(request):
        raise httpx.ConnectError("SECRET", request=request)

    client = PersonalAPIClient(settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(BridgeError, match="connection failed"):
        await client.execute(CATALOG["get_activity_types"], {})
    await client.aclose()


async def test_expired_token_is_renewed():
    count = 0

    def handler(request):
        nonlocal count
        if request.method == "POST":
            count += 1
            return httpx.Response(200, json={"access_token": "ok", "expires_in": 1})
        return httpx.Response(200, json=[])

    client = PersonalAPIClient(settings(), transport=httpx.MockTransport(handler))
    for _ in range(2):
        await client.execute(CATALOG["get_activity_types"], {})
    assert count == 2
    await client.aclose()


def test_catalog_schemas_and_config(monkeypatch):
    assert len(CATALOG) == 28
    assert "test-secret-key" not in repr(settings())
    assert settings(region="china").base_url == "https://personal.connectapi.garmin.cn"
    monkeypatch.setenv("GARMIN_PERSONAL_API_KEY", "SECRET\n")
    with pytest.raises(BridgeError) as error:
        Settings.from_env()
    assert "SECRET" not in str(error.value)
    monkeypatch.setenv("GARMIN_PERSONAL_API_KEY", "valid-key")
    assert Settings.from_env().api_key.get_secret_value() == "valid-key"
    for operation in CATALOG.values():
        assert operation.path.startswith("/")
        assert not operation.path.startswith("//")
        json.dumps(operation.schema)


@pytest.mark.parametrize(
    "name,args",
    [
        ("get_activity", {"activityId": "https://evil.invalid"}),
        ("get_activity", {"activityId": True}),
        ("get_activity", {}),
        ("get_activity", {"activityId": 1, "url": "https://evil.invalid"}),
        ("get_hrv", {"calendarDate": "2026-02-30"}),
        ("get_steps_range", {"startDate": "2026-11-20", "endDate": "2026-11-19"}),
        ("search_activities", {"limit": 1001}),
    ],
)
def test_invalid_arguments(name, args):
    with pytest.raises(BridgeError):
        CATALOG[name].prepare(args)


async def test_token_status_and_invalid_json_are_safe():
    response = httpx.Response(403, text="SECRET")
    client = PersonalAPIClient(settings(), transport=httpx.MockTransport(lambda _: response))
    with pytest.raises(BridgeError, match="Access denied"):
        await client.execute(CATALOG["get_activity_types"], {})
    response = httpx.Response(200, text="SECRET not json")
    with pytest.raises(BridgeError, match="Unsupported token response"):
        await client.execute(CATALOG["get_activity_types"], {})
    await client.aclose()


def test_every_catalog_operation_binds_its_required_inputs():
    from jsonschema import Draft202012Validator

    for operation in CATALOG.values():
        Draft202012Validator.check_schema(operation.schema)
        arguments = {}
        for name in operation.schema["required"]:
            schema = operation.schema["properties"][name]
            arguments[name] = 123 if schema["type"] == "integer" else "2026-11-20"
        path, query = operation.prepare(arguments)
        assert "{" not in path and "}" not in path
        assert all(name not in query for name in operation.path_parameters)


async def test_bad_arguments_do_not_exchange_credentials():
    def handler(request):
        pytest.fail("Invalid tool input must never reach the network")

    client = PersonalAPIClient(settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(BridgeError):
        await client.execute(CATALOG["get_activity"], {"activityId": -1})
    await client.aclose()
