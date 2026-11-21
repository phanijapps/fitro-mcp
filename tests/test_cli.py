from pathlib import Path

import pytest

from fitro_mcp.__main__ import main


@pytest.fixture(autouse=True)
def private_test_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)


def test_cli_version_without_credentials(monkeypatch, capsys):
    monkeypatch.delenv("GARMIN_PERSONAL_API_KEY", raising=False)
    monkeypatch.setattr("sys.argv", ["fitro-mcp", "--version"])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 0
    assert capsys.readouterr().out.strip() == "1.0.0"


def test_cli_invalid_configuration_has_no_protocol_noise(monkeypatch, capsys):
    monkeypatch.setenv("GARMIN_PERSONAL_API_KEY", "private\nkey")
    monkeypatch.setattr("sys.argv", ["fitro-mcp"])
    with pytest.raises(SystemExit) as error:
        main()
    output = capsys.readouterr()
    assert error.value.code == 2
    assert output.out == ""
    assert "private" not in output.err
    assert "Invalid configuration" in output.err


def test_cli_runs_server(monkeypatch):
    started = []

    async def serve(settings):
        started.append(settings.region)

    monkeypatch.setenv("GARMIN_PERSONAL_API_KEY", "synthetic-key")
    monkeypatch.setattr("sys.argv", ["fitro-mcp", "--debug"])
    monkeypatch.setattr("fitro_mcp.__main__.serve", serve)
    main()
    assert started == ["global"]


def test_cli_keyboard_interrupt(monkeypatch):
    async def serve(settings):
        raise KeyboardInterrupt

    monkeypatch.setenv("GARMIN_PERSONAL_API_KEY", "synthetic-key")
    monkeypatch.setattr("sys.argv", ["fitro-mcp"])
    monkeypatch.setattr("fitro_mcp.__main__.serve", serve)
    main()


def test_unexpected_startup_error_is_sanitized(monkeypatch, capsys, tmp_path):
    async def serve(settings):
        raise RuntimeError("SECRET health payload and key")

    monkeypatch.setenv("GARMIN_PERSONAL_API_KEY", "synthetic-key")
    monkeypatch.setattr("sys.argv", ["fitro-mcp", "--debug"])
    monkeypatch.setattr("fitro_mcp.__main__.serve", serve)
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "SECRET" not in output.err
    content = (tmp_path / ".starbridge/fitro.log").read_text()
    assert "internal_error" in content
    assert "SECRET" not in content
