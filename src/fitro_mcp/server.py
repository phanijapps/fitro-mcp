"""MCP composition with domain tools, progressive discovery and structured results."""

import base64
import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from fitro_mcp import __version__
from fitro_mcp.catalog import load_catalog
from fitro_mcp.client import PersonalAPIClient
from fitro_mcp.config import Settings
from fitro_mcp.diagnostics import REQUEST_ID, event
from fitro_mcp.discovery import (
    DISCOVER_SCHEMA,
    DOMAINS,
    OUTPUT_SCHEMA,
    discover,
    resolve,
    tool_schema,
    validate,
)
from fitro_mcp.errors import BridgeError
from fitro_mcp.resources import register_resources


def create_server(settings: Settings) -> Server[PersonalAPIClient]:
    """Compose an isolated stdio server with four domain tools and offline discovery."""
    catalog = load_catalog()
    schemas = {domain: tool_schema(catalog, domain) for domain in DOMAINS}

    @asynccontextmanager
    async def lifespan(_server: Server[PersonalAPIClient]) -> AsyncIterator[PersonalAPIClient]:
        """Own the shared HTTP pool/token cache until this server session closes."""
        client = PersonalAPIClient(settings)
        try:
            yield client
        finally:
            await client.aclose()

    server = Server(
        "fitro-mcp",
        version=__version__,
        lifespan=lifespan,
        instructions="Use discover for domains and operation schemas, then the corresponding "
        "activity, health, wellness or profile tool. Resources provide the same offline guide. "
        "Request only relevant personal data. Dates are YYYY-MM-DD; prefer narrow ranges.",
    )

    # MCP SDK v1 decorators are untyped; keep exceptions at the SDK boundary.
    @server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
    async def list_tools() -> list[types.Tool]:
        """Advertise only compact contracts; exact operation schemas are loaded on demand."""
        return [
            types.Tool(
                name=name,
                description=(
                    "Offline discovery: browse domains, search operations, or retrieve one "
                    "operation's exact parameter schema and example."
                )
                if name == "discover"
                else DOMAINS[name] + " Use discover for exact operation parameters.",
                inputSchema=DISCOVER_SCHEMA if name == "discover" else schemas[name],
                outputSchema=OUTPUT_SCHEMA,
                annotations=types.ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=name != "discover",
                ),
            )
            for name in ["discover", *DOMAINS]
        ]

    @server.call_tool(validate_input=False)  # type: ignore[untyped-decorator]
    async def call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        """Validate, dispatch and serialize one call without leaking diagnostic inputs."""
        request_id = uuid4().hex
        context_token = REQUEST_ID.set(request_id)
        started = time.monotonic()
        envelope: dict[str, Any] = {"request_id": request_id, "data": None}
        failed = False
        try:
            event("request_started")
            if name == "discover":
                envelope["data"] = discover(catalog, arguments)
            elif name in DOMAINS:
                validate(schemas[name], arguments)
                operation = resolve(catalog, name, arguments["operation"])
                operation.prepare(arguments["parameters"])
                result = await server.request_context.lifespan_context.execute(
                    operation, arguments["parameters"]
                )
                if operation.binary:
                    result = {
                        "media_type": "application/zip",
                        "encoding": "base64",
                        "data": base64.b64encode(result).decode("ascii"),
                    }
                envelope["data"] = {"operation": arguments["operation"], "result": result}
            else:
                raise BridgeError("Unknown tool. Use tools/list to discover supported domains.")
            # Reject nonstandard upstream JSON before constructing a protocol result.
            json.dumps(envelope, allow_nan=False)
            event("request_completed", duration_ms=int((time.monotonic() - started) * 1000))
        except BridgeError as exc:
            failed = True
            envelope["data"] = None
            envelope["error"] = {"code": "request_failed", "message": str(exc)}
            event("request_rejected", level=logging.WARNING)
        except Exception:
            failed = True
            envelope["data"] = None
            envelope["error"] = {"code": "internal_error", "message": "Unexpected internal error."}
            event("internal_error", level=logging.ERROR)
        finally:
            REQUEST_ID.reset(context_token)
        return types.CallToolResult(
            isError=failed,
            structuredContent=envelope,
            content=[types.TextContent(type="text", text=json.dumps(envelope, allow_nan=False))],
        )

    register_resources(server, catalog)
    return server


async def serve(settings: Settings) -> None:
    """Run the standard MCP handshake and stdio transport until the client exits."""
    server = create_server(settings)
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())
