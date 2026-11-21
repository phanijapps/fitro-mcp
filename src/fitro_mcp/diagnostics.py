"""Private, rotating, allowlisted diagnostics without request or health content."""

import json
import logging
import os
import re
import stat
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from io import TextIOWrapper
from logging.handlers import RotatingFileHandler
from pathlib import Path

from filelock import FileLock

from fitro_mcp.errors import BridgeError

MAX_LOG_BYTES = 1_000_000
BACKUP_COUNT = 3
REQUEST_ID: ContextVar[str | None] = ContextVar("diagnostic_request_id", default=None)
EVENTS = frozenset(
    {
        "server_started",
        "server_stopped",
        "request_started",
        "request_completed",
        "request_rejected",
        "request_failed",
        "internal_error",
        "http_completed",
        "http_failed",
        "token_cache_hit",
        "token_exchange",
        "token_renewal",
    }
)
LOGGER = logging.getLogger("fitro.diagnostics")
LOGGER.addHandler(logging.NullHandler())
LOGGER.propagate = False


class SafeFormatter(logging.Formatter):
    """Serialize an allowlist only; ignore arbitrary messages, extras and exceptions."""

    def format(self, record: logging.LogRecord) -> str:
        """Never serialize exception text, stack traces or caller-provided messages."""
        event = getattr(record, "safe_event", "")
        if event not in EVENTS:
            event = "internal_error"
        data: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": (
                "error"
                if record.levelno >= logging.ERROR
                else "warning"
                if record.levelno >= logging.WARNING
                else "debug"
            ),
            "event": event,
        }
        request_id = getattr(record, "safe_request_id", None)
        if isinstance(request_id, str) and re.fullmatch(r"[0-9a-f]{32}", request_id):
            data["request_id"] = request_id
        for field in ("status", "duration_ms"):
            value = getattr(record, "safe_" + field, None)
            if type(value) is int and 0 <= value <= (599 if field == "status" else 86_400_000):
                data[field] = value
        return json.dumps(data, separators=(",", ":"))


class PrivateRotatingHandler(RotatingFileHandler):
    """Open logs privately, refuse links, and avoid stderr exception dumps."""

    def __init__(self, filename: Path):
        """Coordinate rotation across clients sharing the same private directory."""
        self._process_lock = FileLock(filename.parent / ".diagnostics.lock", timeout=5, mode=0o600)
        super().__init__(
            filename, maxBytes=MAX_LOG_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
        )

    def emit(self, record: logging.LogRecord) -> None:
        """Reopen under an interprocess lock so another client's rotation is observed."""
        try:
            with self._process_lock:
                if self.stream is not None:
                    self.stream.close()
                    self.stream = None
                super().emit(record)
        except Exception:
            self.handleError(record)

    def _open(self) -> TextIOWrapper:
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.baseFilename, flags, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise OSError("Unsafe log file")
            os.fchmod(fd, 0o600)
            return os.fdopen(fd, "a", encoding="utf-8")
        except BaseException:
            os.close(fd)
            raise

    def handleError(self, record: logging.LogRecord) -> None:
        """Report file failures without dumping the original record or exception."""
        print("Fitro could not write diagnostics.", file=sys.stderr)


def configure_logging(*, debug: bool = False) -> PrivateRotatingHandler:
    """Create ~/.starbridge logs with private POSIX permissions and bounded rotation."""
    try:
        directory = Path.home() / ".starbridge"
        directory.mkdir(mode=0o700, exist_ok=True)
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or (hasattr(os, "getuid") and info.st_uid != os.getuid()):
            raise OSError("Unsafe log directory")
        directory.chmod(0o700)
        # Refuse pre-existing links and make retained backups private, too.
        for name in [
            "fitro.log",
            ".diagnostics.lock",
            *(f"fitro.log.{i}" for i in range(1, 4)),
        ]:
            path = directory / name
            if path.is_symlink():
                raise OSError("Unsafe log file")
            if path.exists():
                if not path.is_file() or path.stat().st_nlink != 1:
                    raise OSError("Unsafe log file")
                path.chmod(0o600)
        handler = PrivateRotatingHandler(directory / "fitro.log")
    except OSError:
        raise BridgeError("Cannot initialize private diagnostics in ~/.starbridge.") from None
    handler.setFormatter(SafeFormatter())
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.DEBUG if debug else logging.WARNING)
    # SDK/HTTP loggers may include request bodies, paths and identifiers. Their
    # output is excluded even in debug mode; only this module writes diagnostics.
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(logging.NullHandler())
    logging.lastResort = None
    return handler


def event(
    name: str,
    *,
    level: int = logging.DEBUG,
    status: int | None = None,
    duration_ms: int | None = None,
) -> None:
    """Emit a fixed event with numeric metadata and an unrelated diagnostic ID."""
    if name not in EVENTS:
        raise ValueError("Unknown diagnostic event")
    LOGGER.log(
        level,
        "",
        extra={
            "safe_event": name,
            "safe_request_id": REQUEST_ID.get(),
            "safe_status": status,
            "safe_duration_ms": duration_ms,
        },
    )
