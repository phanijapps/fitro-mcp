# Contributing

Read [AGENTS.md](AGENTS.md) for the repository map, constraints and definition of done.
The project uses uv, a `src/` layout, the official MCP Python SDK and strict mypy.

```bash
uv sync --locked
uv run pre-commit install  # Optional; requires a Git checkout.
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run pip-audit
uv build
uv run twine check dist/*
```

Run `uv lock` only for intentional metadata/dependency changes. Keep supported Python
versions installable from the same lockfile. Tests use synthetic tokens and HTTPX
transports; no real API key or health account is needed.

To add a documented GET endpoint, follow the worked extension procedure in
[architecture](docs/architecture.md) and [code reference](docs/code-reference.md).
Assign it exactly one domain, preserve upstream parameter names and units, update
its closed input schema, and test positive/invalid inputs and cross-domain rejection.
Do not expand the public tool count to mirror endpoint count.

Keep docstrings focused on contracts, side effects, errors and resource ownership.
Explain security-sensitive choices where they occur. Never add payload logging,
credential fixtures, arbitrary URL access or live API calls to automated checks.

Before a release, check both built distributions using `scripts/smoke_test.py` in
an isolated environment. See [publishing](docs/publishing.md) for exact commands.
Tests do not establish that every upstream endpoint or account region works live;
report manual verification separately and without saving data.

For security issues, follow [SECURITY.md](SECURITY.md). No public issue should
include an API key, access token, upstream error body or personal health payload.
