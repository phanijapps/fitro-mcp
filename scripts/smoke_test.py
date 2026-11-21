"""Verify an installed distribution through its actual console and MCP transport.

Run with the target environment's Python, outside editable installs:
    /path/to/environment/bin/python scripts/smoke_test.py
No real credential or upstream API request is used.
"""

import asyncio
import os
import subprocess
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import ResourceTemplateReference
from pydantic import AnyUrl


def require(condition: bool, message: str) -> None:
    """Fail a release smoke check independently of Python's optimization mode."""
    if not condition:
        raise RuntimeError(message)


async def check_protocol() -> None:
    """Exercise a subprocess using synthetic credentials and a temporary log home."""
    with tempfile.TemporaryDirectory(prefix="fitro-smoke-") as temporary_home:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "fitro_mcp", "--debug"],
            env={
                **os.environ,
                "HOME": temporary_home,
                "GARMIN_PERSONAL_API_KEY": "synthetic-smoke-key",
            },
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            initialized = await session.initialize()
            require(initialized.serverInfo.name == "fitro-mcp", "Wrong server identity")
            require(initialized.serverInfo.version == version("fitro-mcp"), "Wrong server version")
            tools = (await session.list_tools()).tools
            require(
                {tool.name for tool in tools}
                == {
                    "discover",
                    "activity",
                    "health",
                    "wellness",
                    "profile",
                },
                "Wrong tool inventory",
            )
            result = await session.call_tool(
                "discover",
                {
                    "domain": "health",
                    "operation": "menstrual_cycle_day",
                },
            )
            require(not result.isError, "Offline operation discovery failed")
            require(result.structuredContent is not None, "Missing structured output")
            require(len((await session.list_resources()).resources) == 5, "Wrong resource count")
            require(
                len((await session.list_resource_templates()).resourceTemplates) == 2,
                "Wrong resource-template count",
            )
            document = await session.read_resource(
                AnyUrl("fitro://operations/wellness/sleep_range")
            )
            require(bool(document.contents), "Missing operation resource")
            completed = await session.complete(
                ResourceTemplateReference(type="ref/resource", uri="fitro://domains/{domain}"),
                {"name": "domain", "value": "he"},
            )
            require(completed.completion.values == ["health"], "Completion failed")
        log = (Path(temporary_home) / ".starbridge/fitro.log").read_text()
        require("server_started" in log, "Debug logging was not enabled")
        require(
            all(
                private not in log
                for private in [
                    "synthetic-smoke-key",
                    "menstrual",
                    "sleep_range",
                    "health",
                ]
            ),
            "Private content reached logs",
        )


def main() -> None:
    """Verify package metadata, the CLI version, and offline MCP integration."""
    installed = version("fitro-mcp")
    result = subprocess.run(
        [sys.executable, "-m", "fitro_mcp", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    require(result.stdout.strip() == installed, "CLI/package versions differ")
    asyncio.run(check_protocol())
    print(f"Fitro MCP {installed}: installed-package smoke checks passed.")


if __name__ == "__main__":
    main()
