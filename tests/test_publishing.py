import importlib.util
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def publisher():
    path = Path(__file__).resolve().parents[1] / "scripts/publish.py"
    spec = importlib.util.spec_from_file_location("fitro_release_publisher", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_token_stops_before_upload(publisher, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("UV_PUBLISH_TOKEN", raising=False)
    monkeypatch.setattr("sys.argv", ["publish.py", "--token-file", str(tmp_path / "missing")])
    with pytest.raises(SystemExit) as error:
        publisher.main()
    assert error.value.code == 2
    assert "requires UV_PUBLISH_TOKEN" in capsys.readouterr().err


@pytest.mark.parametrize("unsafe", ["public", "symlink"])
def test_unsafe_token_file_is_rejected(publisher, tmp_path, monkeypatch, unsafe):
    monkeypatch.delenv("UV_PUBLISH_TOKEN", raising=False)
    token = tmp_path / "token"
    token.write_text("synthetic-secret")
    if unsafe == "public":
        token.chmod(0o644)
    else:
        target = tmp_path / "target"
        token.rename(target)
        token.symlink_to(target)
    monkeypatch.setattr("sys.argv", ["publish.py", "--token-file", str(token)])
    with pytest.raises(SystemExit) as error:
        publisher.main()
    assert error.value.code == 2


def test_publish_uses_exact_artifacts_and_redacts_token(publisher, tmp_path, monkeypatch, capsys):
    token = tmp_path / "token"
    token.write_text("synthetic-private-pypi-token")
    token.chmod(0o600)
    artifacts = tmp_path / "dist/1.0.0"
    artifacts.mkdir(parents=True)
    expected = [
        artifacts / "fitro_mcp-1.0.0-py3-none-any.whl",
        artifacts / "fitro_mcp-1.0.0.tar.gz",
    ]
    for path in expected:
        path.touch()
    monkeypatch.delenv("UV_PUBLISH_TOKEN", raising=False)
    monkeypatch.setattr(publisher, "__file__", str(tmp_path / "scripts/publish.py"))
    monkeypatch.setattr(publisher.shutil, "which", lambda _: "/usr/bin/uv")
    monkeypatch.setattr("sys.argv", ["publish.py", "--token-file", str(token)])
    calls = []

    def upload(command, **kwargs):
        calls.append(command)
        assert command[-2:] == [str(path) for path in expected]
        assert kwargs["env"]["UV_PUBLISH_TOKEN"] == token.read_text()
        assert token.read_text() not in " ".join(command)
        return subprocess.CompletedProcess(
            command, 0, stdout=token.read_text(), stderr=token.read_text()
        )

    monkeypatch.setattr(publisher.subprocess, "run", upload)
    with pytest.raises(SystemExit) as error:
        publisher.main()
    assert error.value.code == 0
    assert len(calls) == 1
    output = capsys.readouterr()
    assert "synthetic-private-pypi-token" not in output.out + output.err
    assert "<redacted>" in output.out
