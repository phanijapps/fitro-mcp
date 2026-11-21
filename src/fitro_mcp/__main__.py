"""Console entry point; stdout is reserved exclusively for the MCP protocol."""

import argparse
import asyncio
import logging
import sys

from fitro_mcp import __version__
from fitro_mcp.config import Settings
from fitro_mcp.diagnostics import LOGGER, configure_logging, event
from fitro_mcp.errors import BridgeError
from fitro_mcp.server import serve


def main() -> None:
    """Start the local stdio server without accepting secrets on the command line."""
    parser = argparse.ArgumentParser(description="Fitro personal fitness MCP server (stdio)")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--debug", action="store_true", help="Enable private rotating diagnostics")
    args = parser.parse_args()
    handler = None
    try:
        handler = configure_logging(debug=args.debug)
        event("server_started")
        asyncio.run(serve(Settings.from_env()))
    except BridgeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from None
    except KeyboardInterrupt:
        pass
    except Exception:
        event("internal_error", level=logging.ERROR)
        print("Fitro stopped after an internal error.", file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        if handler is not None:
            event("server_stopped")
            LOGGER.removeHandler(handler)
            handler.close()


if __name__ == "__main__":
    main()
