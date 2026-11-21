import json
import logging
import stat
from pathlib import Path

import httpx
import pytest
from test_client import settings

from fitro_mcp.catalog import load_catalog
from fitro_mcp.client import PersonalAPIClient
from fitro_mcp.diagnostics import (
    BACKUP_COUNT,
    LOGGER,
    MAX_LOG_BYTES,
    REQUEST_ID,
    SafeFormatter,
    configure_logging,
    event,
)
from fitro_mcp.errors import BridgeError


@pytest.fixture
def logs(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    root = logging.getLogger()
    original = root.handlers[:]
    last_resort = logging.lastResort
    handlers = []

    def configure(debug=False):
        handler = configure_logging(debug=debug)
        handlers.append(handler)
        return handler

    yield tmp_path / ".starbridge", configure
    for handler in handlers:
        LOGGER.removeHandler(handler)
        handler.close()
    root.handlers[:] = original
    logging.lastResort = last_resort


def test_private_permissions_default_level_and_rotation(logs):
    directory, configure = logs
    handler = configure()
    event("request_started")
    assert (directory / "fitro.log").read_text() == ""
    event("request_failed", level=logging.WARNING)
    assert "request_failed" in (directory / "fitro.log").read_text()
    LOGGER.setLevel(logging.DEBUG)
    # Fill near the real 1 MB boundary and cross it; repeated rotation retains 3 backups.
    for _ in range(5):
        handler.stream.write(" " * (MAX_LOG_BYTES - 10 - handler.stream.tell()))
        handler.stream.flush()
        event("request_completed", status=200, duration_ms=12)
    assert handler.maxBytes == MAX_LOG_BYTES == 1_000_000
    assert handler.backupCount == BACKUP_COUNT == 3
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert len(list(directory.glob("fitro.log*"))) == 4
    for path in directory.iterdir():
        assert path.stat().st_size <= MAX_LOG_BYTES
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_formatter_never_serializes_messages_exceptions_or_extra_data():
    record = logging.LogRecord(
        "any", logging.ERROR, "private/path", 1, "HEALTH SECRET %s", ("token",), None
    )
    record.exc_text = "SENSITIVE traceback"
    record.safe_event = "invalid HEALTH"
    record.safe_request_id = "activity-id"
    record.safe_status = "patient-value"
    record.safe_duration_ms = -1
    record.health = {"cycle": "private"}
    data = json.loads(SafeFormatter().format(record))
    assert data["event"] == "internal_error"
    assert set(data) == {"timestamp", "level", "event"}
    assert "SECRET" not in json.dumps(data)


@pytest.mark.parametrize("raw_token", [False, True])
async def test_debug_http_events_contain_no_health_or_credentials(logs, raw_token):
    directory, configure = logs
    configure(debug=True)

    def handler(request):
        if request.method == "POST":
            if raw_token:
                return httpx.Response(200, text="PRIVATE.PAYLOAD.SIGNATURE")
            return httpx.Response(200, json={"access_token": "PRIVATE-BEARER"})
        return httpx.Response(200, json={"SECRET-health-payload": 99})

    token = REQUEST_ID.set("a" * 32)
    client = PersonalAPIClient(settings(), transport=httpx.MockTransport(handler))
    try:
        for _ in range(2):
            await client.execute(
                load_catalog()["get_menstrual_cycle_summary"], {"calendarDate": "2026-11-20"}
            )
    finally:
        await client.aclose()
        REQUEST_ID.reset(token)
    logging.getLogger("httpx").warning("SECRET http://example.invalid HEALTH")
    content = (directory / "fitro.log").read_text()
    for sensitive in [
        "PRIVATE-BEARER",
        "PRIVATE.PAYLOAD.SIGNATURE",
        "test-secret-key",
        "SECRET",
        "menstrual",
        "health",
        "calendarDate",
        "2026-11-20",
        "connectapi",
        "Authorization",
    ]:
        assert sensitive not in content
    assert "token_cache_hit" in content
    assert "http_completed" in content
    assert '"request_id":"' + "a" * 32 + '"' in content
    for line in content.splitlines():
        assert set(json.loads(line)) <= {
            "timestamp",
            "level",
            "event",
            "request_id",
            "status",
            "duration_ms",
        }


def test_refuses_symlink_log_directory_and_files(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    directory = tmp_path / ".starbridge"
    directory.symlink_to(target, target_is_directory=True)
    with pytest.raises(BridgeError, match="private diagnostics"):
        configure_logging()
    directory.unlink()
    directory.mkdir()
    secret = tmp_path / "private-file"
    secret.write_text("SECRET")
    (directory / "fitro.log").symlink_to(secret)
    with pytest.raises(BridgeError):
        configure_logging()
    assert secret.read_text() == "SECRET"


def test_unknown_event_and_write_failure_are_safe(logs, monkeypatch, capsys):
    _, configure = logs
    handler = configure(debug=True)
    with pytest.raises(ValueError, match="Unknown diagnostic event"):
        event("SECRET")
    monkeypatch.setattr(handler, "shouldRollover", lambda _: 1 / 0)
    event("request_started")
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.strip() == "Fitro could not write diagnostics."


def test_concurrent_processes_share_bounded_logs(tmp_path):
    import os
    import subprocess
    import sys

    script = """
from fitro_mcp.diagnostics import LOGGER, configure_logging, event
handler = configure_logging(debug=True)
handler.maxBytes = 2000
try:
    for i in range(100):
        event("request_completed", status=200, duration_ms=i)
finally:
    LOGGER.removeHandler(handler)
    handler.close()
"""
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", script],
            env={**os.environ, "HOME": str(tmp_path)},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for _ in range(3)
    ]
    for process in processes:
        stdout, stderr = process.communicate(timeout=30)
        assert process.returncode == 0, stderr
        assert stdout == stderr == b""
    files = list((tmp_path / ".starbridge").glob("fitro.log*"))
    assert len(files) == 4
    for path in files:
        assert 0 < path.stat().st_size < 2000
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        for line in path.read_text().splitlines():
            assert json.loads(line)["event"] == "request_completed"
