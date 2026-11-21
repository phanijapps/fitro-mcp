# Verification record

Fitro MCP 1.0.0, checked locally on 2026-11-20. All automated credentials are synthetic.

| Check | Result |
| --- | --- |
| `uv sync --locked` | Pass |
| Ruff lint, including security rules | Pass |
| Ruff formatting | Pass |
| Strict mypy, package sources | Pass |
| Python 3.11.13 | 85 core tests + 4 publishing checks passed; core coverage 97.11% |
| Python 3.12.11 | 85 core tests + 4 publishing checks passed; core coverage 97.11% |
| Python 3.13.7 | 85 core tests + 4 publishing checks passed; core coverage 97.11% |
| Python 3.14.9 | 89 tests passed; 97.07% statement coverage |
| `uv run pip-audit` | No known dependency vulnerabilities reported |
| Wheel and source distribution build | Pass |
| Twine metadata checks, both artifacts | Pass |
| Isolated wheel/source-archive install and console version | Pass; 1.0.0 |
| Installed wheel MCP initialize/tools-list | Pass; five tools, discovery, resources and --debug |
| Offline resource discovery and completion | Pass; five resources, two templates |
| All internal operations through domain dispatch | Pass; all 28 covered |
| Domain boundaries and invalid arguments | Pass; rejected before network access |
| Log privacy, permissions and 1 MB rotation | Pass; three private backups |
| Concurrent processes sharing logs | Pass; interprocess rotation remains bounded |
| Plain-JWT authentication regression tests | Pass; raw/JSON formats, POST-before-GET, caching, renewal, redaction |
| Manual global-region MCP authentication and activity-types call | Pass; only success status reported, no token/body retained |
| Wheel contents | Catalog, typing marker, license present; no .env/caches |

The local project itself is skipped by pip-audit because it is not on PyPI; the
scanner audits installed third-party dependencies, not this project's source.
Ruff/mypy and tests cover source behavior but are not a complete security audit.

CI and local checks cover Python 3.11–3.14. macOS is not verified locally.
No GitHub CI run has been observed. A manual live global-region token exchange and
authenticated activity-types call succeeded through MCP. Other endpoints and the
China region remain unverified live. No registry upload or trademark clearance was
performed. Observed plain-JWT responses and synthetic JSON compatibility formats
are distinguished in [authentication.md](authentication.md).

The serialized `tools/list` tool definitions decreased from 21,705 characters
(28 tools) to 5,073 (five tools), a 76.6% reduction using the same JSON serialization.
This measures definition size, not model token usage or real-model task accuracy.
Tests enforce at least a 50% reduction against the original endpoint definitions.
Real-model operation-selection benchmarks have not been run.
