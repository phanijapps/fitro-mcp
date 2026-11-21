# Fitro MCP

[![PyPI version](https://img.shields.io/pypi/v/fitro-mcp)](https://pypi.org/project/fitro-mcp/)
[![CI](https://github.com/phanijapps/fitro-mcp/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/phanijapps/fitro-mcp/actions/workflows/ci.yml)
[![Python versions](https://img.shields.io/pypi/pyversions/fitro-mcp)](https://pypi.org/project/fitro-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Ask Codex or another MCP-compatible assistant about your Garmin Connect activities,
sleep, steps, heart rate and other health data. Fitro runs locally and provides
read-only access through your Personal API key.

## Quick start

### 1. Get your Personal API key

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.11+.
Linux and WSL are supported; see [platform support](#platform-support) for details.

A **Garmin Connect Personal API key is required**. Create one at the official
[Personal API key setup page](https://developer.garmin.com/gc-developer-program/personal/personal-api/):
sign in, open **Personal API Key**, select **Create Key**, accept the terms and
choose an expiry. Save the key when it is shown. Fitro handles the access-token
exchange automatically.

### 2. Add Fitro to Codex

Paste this into `~/.codex/config.toml` and replace the placeholder with your key:

```toml
[mcp_servers.fitro]
command = "uvx"
args = ["fitro-mcp@1.0.0"]
startup_timeout_sec = 60

[mcp_servers.fitro.env]
GARMIN_PERSONAL_API_KEY = "PASTE_YOUR_PERSONAL_API_KEY_HERE"
```

`uvx` downloads and runs Fitro automatically—no separate package installation is
needed. The default account region is **global**.

### 3. Connect and try it

Restart Codex or reconnect its MCP server, then ask:

> Use Fitro to list the available activity types.

This checks the connection without requesting personal health measurements.
You can then try the [sample prompts](#sample-prompts) below.

If Codex cannot find `uvx`, use its absolute path as `command`. Allow up to a minute
for the first download. See the [official Codex MCP guide](https://developers.openai.com/codex/mcp)
for managing your connections.

### Other MCP clients

For clients that use a `mcpServers` JSON configuration, add:

```json
{
  "mcpServers": {
    "fitro": {
      "command": "uvx",
      "args": ["fitro-mcp@1.0.0"],
      "env": {
        "GARMIN_PERSONAL_API_KEY": "PASTE_YOUR_PERSONAL_API_KEY_HERE"
      }
    }
  }
}
```

Replace the placeholder locally and reconnect the client. Keep your key out of chat
and source control. On POSIX systems, keep configuration files private (`0600`).

### Optional settings

| If you want to… | Change your configuration |
| --- | --- |
| Use a China-region account | Add `FITRO_REGION = "china"` under `[mcp_servers.fitro.env]`. |
| Enable debug logs | Use `args = ["fitro-mcp@1.0.0", "--debug"]`. |
| Check your installed version | Run `uvx fitro-mcp@1.0.0 --version` in a terminal. |

<details>
<summary>Codex CLI setup or an environment-provided key</summary>

You can register a placeholder with the Codex CLI, then edit the real key in
`~/.codex/config.toml`:

```bash
codex mcp add fitro --env GARMIN_PERSONAL_API_KEY=PASTE_YOUR_PERSONAL_API_KEY_HERE -- uvx fitro-mcp@1.0.0
codex mcp list
```

If your Codex launcher already receives `GARMIN_PERSONAL_API_KEY` from its
environment, use this configuration instead:

```toml
[mcp_servers.fitro]
command = "uvx"
args = ["fitro-mcp@1.0.0"]
startup_timeout_sec = 60
env_vars = ["GARMIN_PERSONAL_API_KEY"]
```

Omit the `[mcp_servers.fitro.env]` table in this case so a placeholder cannot
override your environment-provided key. No `.env` files are loaded automatically.

</details>

## Sample prompts

Start with a day or a short date range. Fitro retrieves the data, and your assistant
explains it. Ask the assistant to report unavailable measurements rather than guess.

**Steps and sleep**

> Use Fitro to show my steps and sleep for yesterday. Discover the operations you
> need first, and tell me if any data is unavailable.

**Recent activities**

> Find my five most recent running activities and summarize their distance and duration.

**Sleep comparison**

> Compare my sleep over the last seven days. Point out missing days rather than filling them in.

**Explore available data**

> Use Fitro to show which women's health operations are available. Don't retrieve my data yet.

## Help and troubleshooting

| What you see | What to try |
| --- | --- |
| Fitro tools do not appear | Confirm `uvx` is on your client's PATH, check the config, then reconnect. |
| Authentication fails | Check that you entered a Personal API key and that it has not expired or been revoked. |
| Access denied | Check your account region and API permissions. |
| No data for a day | Try a date with synced measurements; availability depends on your account and device. |
| Rate limit reached | Wait before retrying. |
| Response too large | Request fewer activities or a narrower date range. |
| The process appears to wait in a terminal | Fitro expects an MCP client on stdin; connect it through your client's configuration. |

With `--debug`, local logs are written to **`~/.starbridge/fitro.log`**. They rotate
at 1 MB per file with three backups. The `.starbridge` directory name is intentional.
Match a failed tool result's `request_id` to the log when troubleshooting.

Logs contain generic events, random diagnostic IDs, HTTP status codes and timings.
They exclude health payloads, queried dates, activity IDs, operation names, URLs,
headers, keys, tokens and exception text—even in debug mode. Logs stay local;
stdout is reserved for MCP messages. See [diagnostic internals](docs/code-reference.md#results-and-diagnostics)
for file permissions and rotation details.

## Privacy and personal use

- Fitro reads data; it does not write to your Garmin account or save health payloads
  and access tokens to disk.
- Retrieved data is visible to your MCP client and potentially its model provider.
  Choose a client whose data handling you trust.
- The [Personal API FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/)
  limits the API to an individual's own data and excludes commercial applications
  serving multiple users.

**Independent project. Not affiliated with, endorsed by, or sponsored by Garmin.**
Garmin and Garmin Connect are trademarks of Garmin Ltd. or its subsidiaries. The
Fitro name has not received trademark clearance. The client code is [MIT licensed](LICENSE);
upstream services retain their own terms.

## Technical reference

The details below are for developers and users who want to inspect the MCP interface.

### Technology and verification

Fitro uses Python, the official MCP Python SDK and HTTPX, with uv, Ruff, strict mypy,
synthetic tests and dependency auditing. Five public tools cover 28 reviewed GET
operations. Their serialized definitions are about 77% smaller than the original
28-tool interface; this is a JSON-size measurement, not a model-token benchmark.

Live token exchange and activity-types retrieval have been verified on the global
region. Individual health endpoints and China-region authentication are not fully
verified live. See [authentication](docs/authentication.md) and
[verification](docs/verification.md) for the precise scope.

### Platform support

Python 3.11–3.14 is tested on Linux. macOS follows the same POSIX permission model
but has not been tested locally. Native Windows is not supported in 1.0.0; use WSL.

### Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `GARMIN_PERSONAL_API_KEY` | required | Personal API credential |
| `FITRO_REGION` | `global` | `global` (`.com`) or `china` (`.cn`) |
| `FITRO_TIMEOUT_SECONDS` | `30` | HTTP timeout per network phase, 1–120 seconds |
| `FITRO_MAX_RESPONSE_BYTES` | `8388608` | Decoded response cap, 1 KiB–32 MiB |

No `.env` files are auto-loaded. TLS verification is enabled; redirects and
HTTPX environment proxy configuration are disabled. Only official regional hosts
are reachable through the public configuration. Health data returned by a tool is
visible to your MCP client and potentially its model provider: choose a trusted
client and configure its data handling accordingly.

A 401 triggers one token renewal, then a safe authentication error. A 403 indicates
permissions, 404 missing data, and 429 a rate limit; wait before retrying. Other
HTTP and network failures produce sanitized errors. No automatic retries are made
for rate limits or server errors. Narrow date ranges if responses exceed the cap.

### Operations and progressive discovery

Only five tools appear in `tools/list`. API endpoints are internal operations,
not separate tools:

| Tool | Operations |
| --- | --- |
| `activity` | `activity_types`, `activity`, `activity_workouts`, `search_activities`, `download_activity`, `wellness_activity_range` |
| `health` | `heart_rate`, `heart_rate_zones`, `hrv`, `hrv_range`, `vo2_max_range`, `fitness_age`, `spo2`, `weight_measurements`, `weight_range`, `weight_goals`, `menstrual_cycle_summary`, `menstrual_cycle_day` |
| `wellness` | `daily_summary`, `daily_summaries`, `steps_range`, `stress_range`, `hydration_range`, `body_battery`, `sleep`, `sleep_range`, `food_logs` |
| `profile` | `user_settings` |
| `discover` | Offline domain browsing, operation search, and exact schemas/examples |

Women's health is included in `health`. Each execution tool accepts `operation`
and `parameters`, enforces its domain boundary, and validates the exact operation
schema before any authentication or data request.

An assistant can progressively discover the operation it needs:

1. `discover({})` returns the four domains and operation counts.
2. `discover({"domain": "wellness"})` returns a short operation page.
3. `discover({"domain": "wellness", "operation": "sleep_range"})` returns the
   exact parameter schema, a synthetic example, and its documentation URI.
4. `wellness` executes the operation:

   ```json
   {
     "operation": "sleep_range",
     "parameters": {
       "startDate": "2026-11-01",
       "endDate": "2026-11-07"
     }
   }
   ```

`discover` also accepts `query` (up to 200 characters), `limit` (1–10, default 8),
and `offset` for subsequent pages. It returns `total` and `next_offset`; it never
loads all parameter schemas at once. For example, `{"query": "women"}` finds the
two cycle operations. Discovery is a local keyword search, not another model call.
Known operation contracts can be executed directly without repeating discovery.

All tools return a structured envelope with `request_id` and `data`. Failures set
`isError` and include a safe `error.code` and `error.message`. Query data contains
`operation` and `result`; discovery data contains catalog metadata. A JSON text
fallback carries the same envelope for clients without structured-result support.

Arguments inside `parameters` preserve Swagger names, including `activityId`,
`calendarDate`, `startDate`, and `endDate`. Dates use `YYYY-MM-DD`. Optional
arguments are omitted upstream unless supplied; Swagger defaults are informational.
Activity search accepts `limit` 1–1000 and a nonnegative `start`. There is no
automatic data pagination: advance `start` explicitly. Data is not silently truncated;
responses exceeding the configured cap fail with a safe error. Request small ranges.

Activity downloads return `result` containing `media_type`, `encoding: "base64"`,
and `data`. They are never written to disk. Base64 increases output size; large
files may exceed server or client limits. No arbitrary HTTP or filesystem tools
are exposed.

### MCP resources and completion

The server advertises a guide and four domain resources through `resources/list`:

- `fitro://guide`
- `fitro://domains/{domain}`
- `fitro://operations/{domain}/{operation}`

The last two are also resource templates. Domain resources list all operations
in that domain, while an operation resource supplies its exact schema and example.
`completion/complete` suggests domain names and domain-scoped operation names for
these resource templates. All resource reads and completion requests work offline.

Resources and tools use the same catalog. The `discover` tool provides the same
information for clients that do not expose resources to their model. Server
instructions explain this workflow during initialization. Prompt workflows and
dynamic tool activation are not part of this interface.

**Migration:** the original 28 endpoint tool names are no longer registered. For
example, replace `get_hrv({"calendarDate": "2026-11-20"})` with
`health({"operation": "hrv", "parameters": {"calendarDate": "2026-11-20"}})`.

## Development and alternative installation

For code organization and extension contracts, see the
[code reference](docs/code-reference.md), [architecture](docs/architecture.md),
[contributor guide](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

### Run from a checkout

```bash
uv sync --locked
uv run fitro-mcp --version
```

Use this Codex configuration for local development:

```toml
[mcp_servers.fitro]
command = "uv"
args = ["--directory", "/absolute/path/to/gc-gather-mcp", "run", "--locked", "fitro-mcp"]
startup_timeout_sec = 60

[mcp_servers.fitro.env]
GARMIN_PERSONAL_API_KEY = "PASTE_YOUR_PERSONAL_API_KEY_HERE"
```

A direct Bash run can take the key from your shell:

```bash
read -rsp 'Personal API key: ' GARMIN_PERSONAL_API_KEY; echo
export GARMIN_PERSONAL_API_KEY
uv run fitro-mcp
```

Keys are never accepted as server command-line arguments. Without a connected MCP
client, the server waits for protocol messages on stdin.

### Install with pip

If you prefer to manage a virtual environment instead of using `uvx`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install fitro-mcp==1.0.0
fitro-mcp --version
```

For an MCP client using this installation, set `command` to the absolute path of
that environment's `fitro-mcp` executable and omit the `uvx` package arguments.

### Verify changes

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run pip-audit
uv build
uv run twine check dist/*
```

Tests use synthetic credentials and do not need a live account. Installed-package
checks and release steps are documented in [publishing](docs/publishing.md).

### Release automation

Stable `vMAJOR.MINOR.PATCH` tags trigger GitHub Actions to verify, publish to PyPI,
and create a GitHub Release with matching distribution files and checksums. See
[the publishing guide](docs/publishing.md) for tag creation, reruns and credentials.

[Source](https://github.com/phanijapps/fitro-mcp) ·
[PyPI](https://pypi.org/project/fitro-mcp/) ·
[Releases](https://github.com/phanijapps/fitro-mcp/releases) ·
[Changelog](CHANGELOG.md) ·
[Official API Swagger](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/)
