# Agent guide

## Overview

Fitro MCP is a Python 3.11+ stdio MCP server for an individual user's Garmin
Connect Personal API. It exchanges a personal API key for a bearer token, then
exposes five public tools over reviewed GET operations. Keep the neutral package name
`fitro-mcp` and the import namespace `fitro_mcp` consistent.

## Repo map

- `src/fitro_mcp/__main__.py`: console entry, sanitized startup, stdio only.
- `config.py`: validated environment settings and fixed regional HTTPS hosts.
- `catalog.py`: input validation and endpoint binding.
- `discovery.py`: domain boundaries, compact tool contracts and offline discovery.
- `resources.py`: offline MCP documentation resources/templates and completion.
- `diagnostics.py`: allowlisted private rotating log events and correlation context.
- `data/operations.json`: reviewed endpoint allowlist and public input schemas.
- `client.py`: HTTP lifecycle, size limits, token cache and renewal.
- `authentication.py`: private token response parsing (plain JWT and compatible JSON).
- `server.py`: MCP listing, dispatch, error and binary serialization.
- `errors.py`: safe public errors; `__init__.py`: package version.
- `tests/`: mocked HTTP security/behavior checks and a real stdio MCP handshake.
- `docs/`: authentication assumptions, architecture, publishing.
- `pyproject.toml`, `uv.lock`: metadata, tooling configuration, reproducible development.
- `scripts/smoke_test.py`: installed-wheel/source archive protocol verification.
- `scripts/publish.py`: exact-artifact PyPI upload with local credential handling.
- `examples/codex.toml`: versioned end-user Codex setup.
- `.github/workflows/`: quality, dependency audit and package build checks.

## Build instructions

Use uv. Run `uv sync --locked` on an unchanged checkout. After intentional
dependency changes, run `uv lock` and review the diff, then sync. Never install
project tooling into the system Python. Build with `uv build`; check distribution
metadata using `uv run twine check dist/*`. Entry points are `uv run
fitro-mcp` and `uv run python -m fitro_mcp`.

## Design and security rules

- Keep the protocol layer thin and HTTP independently testable through injected transports.
- Keep all operations read-only. New endpoints need reviewed documentation and tests.
- Expose only activity, health (including women's health), wellness, profile and discover.
- Keep resource contracts, discovery and tool validation backed by the same catalog.
- Region defaults to global; --debug enables local diagnostics in ~/.starbridge.
- Cap each log at 1,000,000 bytes with three backups; use private permissions.
- Log only fixed generic events, random request IDs, status codes and timings.
  Exclude arguments, dates, domains/operations, health content and exception text.
- Never accept arbitrary upstream URLs, origins, headers, or methods from tool input.
- Never return/log credentials, upstream error bodies, raw validation exceptions,
  request URLs, or health data in diagnostic messages.
- Do not print non-protocol output to stdout. Do not persist tokens or health data.
- Retain verified TLS, no redirects, bounded response reads, and timeouts.
- Validate inputs before authentication; schemas reject unknown keys and malformed dates.
- Preserve the local stdio boundary. Remote hosting/auth is a separate design task.
- Update documentation when tool contracts, settings or authentication change.
- Avoid live API calls in automated checks. Use synthetic credentials and transport mocks.

## Verification

Run from the repository root:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run pip-audit
uv build
uv run twine check dist/*
```

Pytest enforces at least 85% coverage. Check that wheel contents include
`data/operations.json`, `py.typed`, and license metadata. Install the wheel in a
clean environment and run `scripts/smoke_test.py` for metadata, CLI version,
MCP initialize/tools-list (five tools), offline resources and completions.
CI tests all supported Python minor versions. Audit findings require remediation
or a documented, narrowly justified exception; never silently suppress them.

## Definition of done

- The intended behavior works through MCP, with discoverable accurate tool schemas.
- Positive, invalid-input, upstream-error, and credential-redaction paths are covered.
- Required verification passes and distribution artifacts build and install.
- README, agent guide, and relevant design/assumption docs reflect the implementation.
- No secrets, local environments, generated distributions or personal data are committed.
- Verification reports distinguish mocked protocol/API tests from live upstream tests.
- Publishing needs the owner's registry identity/name checks; do not claim a release
  or legal clearance that has not happened.
