"""Offline MCP resources and completions backed by the same operation catalog."""

import json
from typing import Any

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from pydantic import AnyUrl

from fitro_mcp.catalog import Operation
from fitro_mcp.client import PersonalAPIClient
from fitro_mcp.discovery import DOMAINS, GUIDE, describe, discover, operation_id, resolve

DOMAIN_TEMPLATE = "fitro://domains/{domain}"
OPERATION_TEMPLATE = "fitro://operations/{domain}/{operation}"


def register_resources(server: Server[PersonalAPIClient], catalog: dict[str, Operation]) -> None:
    """Register context documents and resource argument completion without API access."""

    @server.list_resources()  # type: ignore[no-untyped-call, untyped-decorator]
    async def list_resources() -> list[types.Resource]:
        """List the guide and domain indexes without fetching any account data."""
        return [
            types.Resource(
                uri=AnyUrl("fitro://guide"),
                name="Fitro guide",
                mimeType="text/plain",
                description="Discover operations, query domains and enable private diagnostics.",
            ),
            *[
                types.Resource(
                    uri=AnyUrl(f"fitro://domains/{domain}"),
                    name=domain,
                    description=description,
                    mimeType="application/json",
                )
                for domain, description in DOMAINS.items()
            ],
        ]

    @server.list_resource_templates()  # type: ignore[no-untyped-call, untyped-decorator]
    async def templates() -> list[types.ResourceTemplate]:
        """Advertise parameterized documentation addresses, not data endpoints."""
        return [
            types.ResourceTemplate(
                uriTemplate=DOMAIN_TEMPLATE, name="Domain operations", mimeType="application/json"
            ),
            types.ResourceTemplate(
                uriTemplate=OPERATION_TEMPLATE,
                name="Operation contract",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()  # type: ignore[no-untyped-call, untyped-decorator]
    async def read_resource(uri: AnyUrl) -> list[ReadResourceContents]:
        """Resolve only known catalog URIs; never forward a URI to the network."""
        parts = str(uri).removeprefix("fitro://").split("/")
        data: Any
        if str(uri) == "fitro://guide":
            return [ReadResourceContents(content=GUIDE, mime_type="text/plain")]
        if len(parts) == 2 and parts[0] == "domains" and parts[1] in DOMAINS:
            data = discover(catalog, {"domain": parts[1], "limit": 10})
            if data["next_offset"] is not None:
                page = discover(catalog, {"domain": parts[1], "offset": data["next_offset"]})
                data["operations"].extend(page["operations"])
                data["next_offset"] = page["next_offset"]
        elif len(parts) == 3 and parts[0] == "operations" and parts[1] in DOMAINS:
            try:
                data = describe(resolve(catalog, parts[1], parts[2]))
            except Exception:
                raise ValueError("Unknown resource.") from None
        else:
            raise ValueError("Unknown resource.")
        return [ReadResourceContents(content=json.dumps(data), mime_type="application/json")]

    @server.completion()  # type: ignore[no-untyped-call, untyped-decorator]
    async def complete(
        ref: types.PromptReference | types.ResourceTemplateReference,
        argument: types.CompletionArgument,
        context: types.CompletionContext | None,
    ) -> types.Completion:
        """Complete public domain/operation names, scoped by prior template arguments."""
        values: list[str] = []
        if isinstance(ref, types.ResourceTemplateReference) and ref.uri in (
            DOMAIN_TEMPLATE,
            OPERATION_TEMPLATE,
        ):
            if argument.name == "domain":
                values = list(DOMAINS)
            elif argument.name == "operation" and ref.uri == OPERATION_TEMPLATE:
                domain = (context.arguments or {}).get("domain") if context else None
                values = [operation_id(op) for op in catalog.values() if op.domain == domain]
        values = [value for value in values if value.startswith(argument.value[:200])]
        return types.Completion(values=values, total=len(values), hasMore=False)
