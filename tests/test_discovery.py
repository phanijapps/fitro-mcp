import json

import pytest

from fitro_mcp.catalog import load_catalog
from fitro_mcp.discovery import (
    describe,
    discover,
    operation_id,
)
from fitro_mcp.errors import BridgeError


def test_domains_search_pagination_and_examples():
    catalog = load_catalog()
    domains = discover(catalog, {})["domains"]
    assert sum(domain["operations"] for domain in domains) == 28
    women = discover(catalog, {"query": "women health"})
    assert len(women["operations"]) == 2
    assert all(op["domain"] == "health" for op in women["operations"])
    pages = []
    offset = 0
    while offset is not None:
        page = discover(catalog, {"offset": offset, "limit": 3})
        pages.extend(op["operation"] for op in page["operations"])
        offset = page["next_offset"]
    assert len(pages) == len(set(pages)) == 28
    assert discover(catalog, {"query": "nonexistent"})["operations"] == []
    for operation in catalog.values():
        example = describe(operation)["example"]
        operation.prepare(example["parameters"])
        assert example["operation"] == operation_id(operation)


async def test_advertised_schema_size_reduction():
    from mcp.shared.memory import create_connected_server_and_client_session
    from test_client import settings

    from fitro_mcp.server import create_server

    catalog = load_catalog()
    old = [
        {
            "name": op.name,
            "description": op.description,
            "inputSchema": op.schema,
            "annotations": {
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": True,
            },
        }
        for op in catalog.values()
    ]
    async with create_connected_server_and_client_session(create_server(settings())) as session:
        new = (await session.list_tools()).model_dump(exclude_none=True)["tools"]
    assert len(new) == 5
    assert len(json.dumps(new)) < len(json.dumps(old)) / 2


@pytest.mark.parametrize(
    "arguments",
    [
        {"limit": 100},
        {"offset": -1},
        {"query": "x" * 201},
        {"domain": "other"},
        {"domain": "health", "operation": "sleep"},
        {"operation": "hrv"},
    ],
)
def test_discovery_rejects_bad_inputs(arguments):
    with pytest.raises(BridgeError):
        discover(load_catalog(), arguments)
