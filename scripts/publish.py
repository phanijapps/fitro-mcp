"""Publish only the reviewed 1.0.0 artifacts using a locally supplied PyPI token.

Credentials are passed in the subprocess environment, never command-line arguments.
The optional private token file is outside the repository and never copied into it.
No account-data or Garmin credentials are read by this helper.
"""

import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

VERSION = "1.0.0"
TOKEN_FILE = Path.home() / ".config/fitro/pypi-token"


def main() -> None:
    """Require credentials and exact artifact names before invoking the PyPI uploader."""
    parser = argparse.ArgumentParser(description="Publish Fitro MCP 1.0.0 to PyPI")
    parser.add_argument(
        "--token-file",
        type=Path,
        default=TOKEN_FILE,
        help="Private file containing a PyPI API token",
    )
    args = parser.parse_args()
    token = os.environ.get("UV_PUBLISH_TOKEN", "")
    if not token and args.token_file.exists():
        info = args.token_file.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            parser.exit(2, "PyPI token file must be a private regular file (0600 or 0400).\n")
        token = args.token_file.read_text().strip()
    if not token:
        parser.exit(2, "Publishing requires UV_PUBLISH_TOKEN or ~/.config/fitro/pypi-token.\n")
    uv = shutil.which("uv")
    if uv is None:
        parser.exit(2, "Install uv before publishing.\n")
    directory = Path(__file__).resolve().parents[1] / "dist" / VERSION
    artifacts = [
        directory / f"fitro_mcp-{VERSION}-py3-none-any.whl",
        directory / f"fitro_mcp-{VERSION}.tar.gz",
    ]
    if not all(path.is_file() for path in artifacts):
        parser.exit(2, "Build and verify both 1.0.0 artifacts before publishing.\n")
    result = subprocess.run(  # noqa: S603
        [
            uv,
            "publish",
            "--trusted-publishing",
            "never",
            "--publish-url",
            "https://upload.pypi.org/legacy/",
            *(str(path) for path in artifacts),
        ],
        env={**os.environ, "UV_PUBLISH_TOKEN": token},
        capture_output=True,
        text=True,
    )
    # Suppress credential contents even if a future uploader prints an unsafe error.
    print(result.stdout.replace(token, "<redacted>"), end="")
    print(result.stderr.replace(token, "<redacted>"), end="", file=sys.stderr)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
