# Build and publish Fitro MCP

Distribution/executable: `fitro-mcp`. Import namespace: `fitro_mcp`.
The release version must match `pyproject.toml` and `fitro_mcp.__version__`.
Only the package owner should publish releases to their PyPI account. Registry
credentials are separate from `GARMIN_PERSONAL_API_KEY`.

## Prepare and verify

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run pip-audit
uv build --out-dir dist/1.0.0
uv run twine check dist/1.0.0/*.whl dist/1.0.0/*.tar.gz
uv run --isolated --no-project --with dist/1.0.0/fitro_mcp-1.0.0-py3-none-any.whl scripts/smoke_test.py
uv run --isolated --no-project --with dist/1.0.0/fitro_mcp-1.0.0.tar.gz scripts/smoke_test.py
```

The smoke script verifies installed metadata, CLI version, a real MCP subprocess,
five tools, offline discovery, resources/templates/completion and private debug
logging. It uses a synthetic key and never fetches account data. Both distributions
must exclude `.env`, caches, local config, credentials and health payloads.
The explicit source-distribution allowlist helps enforce this boundary.

Review [verification](verification.md), [authentication](authentication.md), and
[CHANGELOG.md](../CHANGELOG.md). Check that the PyPI name is still available (or
owned by the releasing account). Package-name availability is not legal clearance.
The source repository is https://github.com/phanijapps/fitro-mcp. No private
maintainer identity or contact address is invented by the release tooling.

## Supply a PyPI token locally

Prefer trusted publishing when this project has a GitHub repository and an explicit
PyPI Trusted Publisher mapping. This local checkout can publish using a PyPI API
token. For a first upload, the token needs permission to create the project; after
creation, prefer a project-scoped token.

For a local token file, run this in your own Bash terminal (not in chat):

```bash
install -d -m 700 ~/.config/fitro
read -rsp 'PyPI API token: ' FITRO_RELEASE_TOKEN; echo
(umask 077; printf '%s' "$FITRO_RELEASE_TOKEN" > ~/.config/fitro/pypi-token)
unset FITRO_RELEASE_TOKEN
```

This puts the token outside the repository, with user-only permissions. Do not use
your Garmin key here. Do not paste either credential into a chat or commit it.

## Publish the reviewed artifacts

The helper accepts `UV_PUBLISH_TOKEN` or the private token file above:

```bash
uv run python scripts/publish.py
```

It publishes only the exact wheel and source archive for 1.0.0 in `dist/1.0.0/` to
`https://upload.pypi.org/legacy/`. No glob can accidentally upload old development
artifacts. The token goes in the uploader's environment, not its command line.
Uploader output is scrubbed of the token. With no credential, the helper stops
before uploading. A custom private path can be supplied via `--token-file`.

For a direct owner-operated upload, uv also accepts `UV_PUBLISH_TOKEN`:

```bash
uv publish dist/1.0.0/fitro_mcp-1.0.0-py3-none-any.whl dist/1.0.0/fitro_mcp-1.0.0.tar.gz
```

PyPI versions/files are immutable. Do not rebuild or replace artifacts after a
successful upload; increase the version for a subsequent release.

## Verify after upload

```bash
uvx fitro-mcp@1.0.0 --version
uv run --isolated --no-project --with fitro-mcp==1.0.0 scripts/smoke_test.py
```

Confirm PyPI's two download hashes match your reviewed local files. Then use the
[Codex configuration](../examples/codex.toml) and try the README prompt. Keep source
and live verification claims distinct: the automated suite never uses real keys.
See [uv publishing](https://docs.astral.sh/uv/guides/package/#publishing-your-package)
and [PyPI token guidance](https://pypi.org/help/#apitoken) for registry setup.
