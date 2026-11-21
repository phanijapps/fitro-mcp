import base64
import json
import os
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import ResourceTemplateReference
from pydantic import AnyUrl
from test_client import settings

from fitro_mcp.catalog import load_catalog
from fitro_mcp.client import PersonalAPIClient
from fitro_mcp.discovery import DOMAINS, operation_id
from fitro_mcp.resources import OPERATION_TEMPLATE
from fitro_mcp.server import create_server


async def test_mcp_domains_discovery_and_dispatch(monkeypatch):
    calls = []

    async def execute(self, operation, arguments):
        calls.append(operation.name)
        if operation.binary:
            return b"archive"
        if operation.name == "get_user_settings":
            raise RuntimeError("SECRET-health-payload")
        return {"steps": 42}

    monkeypatch.setattr(PersonalAPIClient, "execute", execute)
    async with create_connected_server_and_client_session(create_server(settings())) as session:
        tools = (await session.list_tools()).tools
        assert {t.name for t in tools} == {"discover", *DOMAINS}
        assert all(t.annotations.readOnlyHint for t in tools)
        discovery = await session.call_tool("discover", {})
        assert len(discovery.structuredContent["data"]["domains"]) == 4
        detail = await session.call_tool(
            "discover",
            {
                "domain": "wellness",
                "operation": "sleep_range",
            },
        )
        schema = detail.structuredContent["data"]["parameters_schema"]
        assert "startDate" in schema["properties"]
        assert calls == []
        result = await session.call_tool(
            "wellness",
            {
                "operation": "daily_summary",
                "parameters": {},
            },
        )
        assert result.structuredContent["data"]["result"] == {"steps": 42}
        assert json.loads(result.content[0].text) == result.structuredContent
        binary = await session.call_tool(
            "activity",
            {
                "operation": "download_activity",
                "parameters": {"activityId": 1},
            },
        )
        assert base64.b64decode(binary.structuredContent["data"]["result"]["data"]) == b"archive"
        internal = await session.call_tool(
            "profile",
            {
                "operation": "user_settings",
                "parameters": {},
            },
        )
        assert internal.isError
        assert "SECRET" not in internal.content[0].text
        assert len(internal.structuredContent["request_id"]) == 32


@pytest.mark.parametrize(
    "tool,args",
    [
        ("not_a_tool", {}),
        ("get_activity", {"activityId": 1}),
        ("activity", {"operation": "hrv", "parameters": {"calendarDate": "2026-11-20"}}),
        ("activity", {"operation": "activity", "parameters": {"activityId": "bad"}}),
        ("activity", {"operation": "activity", "parameters": {"activityId": 1}, "url": "bad"}),
        ("health", {"operation": "hrv", "parameters": {"calendarDate": "2026-02-30"}}),
        ("discover", {"operation": "hrv"}),
        ("discover", {"domain": "health", "operation": "unknown"}),
        ("discover", {"domain": "bad"}),
    ],
)
async def test_invalid_domain_calls_never_reach_upstream(monkeypatch, tool, args):
    async def execute(*args):
        pytest.fail("Invalid arguments reached HTTP client")

    monkeypatch.setattr(PersonalAPIClient, "execute", execute)
    async with create_connected_server_and_client_session(create_server(settings())) as session:
        response = await session.call_tool(tool, args)
        assert response.isError
        assert response.structuredContent["data"] is None


async def test_resources_and_completions_are_offline(monkeypatch):
    async def execute(*args):
        pytest.fail("Discovery must not access upstream")

    monkeypatch.setattr(PersonalAPIClient, "execute", execute)
    async with create_connected_server_and_client_session(create_server(settings())) as session:
        assert len((await session.list_resources()).resources) == 5
        assert len((await session.list_resource_templates()).resourceTemplates) == 2
        guide = await session.read_resource(AnyUrl("fitro://guide"))
        assert "discover" in guide.contents[0].text
        for domain in DOMAINS:
            resource = await session.read_resource(AnyUrl(f"fitro://domains/{domain}"))
            body = json.loads(resource.contents[0].text)
            assert body["next_offset"] is None
            assert body["total"] == len(body["operations"])
            for op in body["operations"]:
                detail = await session.read_resource(AnyUrl(op["resource_uri"]))
                assert json.loads(detail.contents[0].text)["operation"] == op["operation"]
        domain = await session.complete(
            ResourceTemplateReference(type="ref/resource", uri=OPERATION_TEMPLATE),
            {"name": "domain", "value": "he"},
        )
        assert domain.completion.values == ["health"]
        operations = await session.complete(
            ResourceTemplateReference(type="ref/resource", uri=OPERATION_TEMPLATE),
            {"name": "operation", "value": "menstrual"},
            context_arguments={"domain": "health"},
        )
        assert len(operations.completion.values) == 2
        invalid = await session.complete(
            ResourceTemplateReference(type="ref/resource", uri="fitro://unknown/{domain}"),
            {"name": "domain", "value": ""},
        )
        assert invalid.completion.values == []
        for uri in [
            "fitro://unknown",
            "fitro://operations/health/invalid",
            "fitro://domains/bad",
            "https://evil.invalid/domains/health",
        ]:
            with pytest.raises(Exception, match="Unknown resource"):
                await session.read_resource(AnyUrl(uri))


async def test_every_operation_is_reachable_through_exactly_one_domain(monkeypatch):
    seen = []

    async def execute(self, operation, arguments):
        seen.append(operation.name)
        return b"zip" if operation.binary else []

    monkeypatch.setattr(PersonalAPIClient, "execute", execute)
    async with create_connected_server_and_client_session(create_server(settings())) as session:
        for op in load_catalog().values():
            parameters = {
                name: 123 if op.schema["properties"][name]["type"] == "integer" else "2026-11-20"
                for name in op.schema["required"]
            }
            result = await session.call_tool(
                op.domain,
                {
                    "operation": operation_id(op),
                    "parameters": parameters,
                },
            )
            assert not result.isError, result
    assert len(seen) == len(set(seen)) == 28


@pytest.mark.parametrize("debug", [False, True])
async def test_real_stdio_handshake(tmp_path, debug):
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "fitro_mcp", *(["--debug"] if debug else [])],
        env={**os.environ, "GARMIN_PERSONAL_API_KEY": "offline-test-key", "HOME": str(tmp_path)},
    )
    async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
        initialized = await session.initialize()
        assert initialized.serverInfo.name == "fitro-mcp"
        assert "discover" in initialized.instructions
        assert initialized.capabilities.resources is not None
        assert initialized.capabilities.completions is not None
        assert len((await session.list_tools()).tools) == 5
        await session.call_tool("discover", {})
    content = (tmp_path / ".starbridge/fitro.log").read_text()
    assert ("server_started" in content) == debug
    assert "offline-test-key" not in content
    assert "health" not in content
