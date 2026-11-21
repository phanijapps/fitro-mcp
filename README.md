# Fitro MCP

[![PyPI version](https://img.shields.io/pypi/v/fitro-mcp)](https://pypi.org/project/fitro-mcp/)
[![CI](https://github.com/phanijapps/fitro-mcp/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/phanijapps/fitro-mcp/actions/workflows/ci.yml)
[![Python versions](https://img.shields.io/pypi/pyversions/fitro-mcp)](https://pypi.org/project/fitro-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Overview

Fitro connects your Garmin Connect data to your AI assistant. Ask about activities,
steps, sleep, heart rate, HRV, weight, nutrition and women's health in plain language.

- **Read-only:** retrieve your own data without changing your Garmin account.
- **Small toolset:** Activity, Health, Wellness, Profile and Discover cover 28 API operations.
- **Local server:** run with `uvx`; no separate package installation is needed.
- **Private diagnostics:** debug logs exclude health data, API keys and tokens.

## Quick MCP Setup

### Before you start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and use Python
3.11+. Linux and WSL are tested; see [platform support](#platform-support) for details.

A **Garmin Connect Personal API key is required**. Get one from the official
[Personal API key setup page](https://developer.garmin.com/gc-developer-program/personal/personal-api/):
sign in, open **Personal API Key**, select **Create Key**, accept the terms and
choose an expiry. Save the key when it is shown. Fitro exchanges it for an access
token automatically.

Choose your client below. Replace placeholders locally, keep keys out of chat and
source control, and use an absolute path to `uvx` if your app cannot find it.
The default account region is **global**. The first launch may take a minute while
`uvx` downloads the package.

### Claude

For **Claude Desktop**, open its local MCP configuration file,
`claude_desktop_config.json`, and merge in:

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

Save and restart Claude Desktop. See the
[official local-server setup guide](https://modelcontextprotocol.io/docs/develop/connect-local-servers)
for locating the configuration file and checking the connection.

<details>
<summary>Claude Code</summary>

Register a placeholder in your user-level configuration:

```bash
claude mcp add --scope user --env GARMIN_PERSONAL_API_KEY=PASTE_YOUR_PERSONAL_API_KEY_HERE --transport stdio fitro -- uvx fitro-mcp@1.0.0
```

Then replace the placeholder locally in the user-level `mcpServers.fitro` entry
in `~/.claude.json`. Start a new Claude Code session and use `/mcp` to check Fitro.
See the [Claude Code MCP guide](https://code.claude.com/docs/en/mcp).

</details>

### ChatGPT

**ChatGPT web does not launch local `uvx` commands directly.** Where your account
supports [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels),
you can connect Fitro's stdio process through OpenAI's `tunnel-client`.

First install `tunnel-client`, create a tunnel associated with your ChatGPT workspace,
and obtain its runtime key using the linked guide. Set `CONTROL_PLANE_API_KEY` and
`GARMIN_PERSONAL_API_KEY` securely in your local environment, then run:

```bash
tunnel-client init --sample sample_mcp_stdio_local --profile fitro --tunnel-id YOUR_TUNNEL_ID --mcp-command "uvx fitro-mcp@1.0.0"
tunnel-client doctor --profile fitro --explain
tunnel-client run --profile fitro
```

Keep the tunnel client running. In ChatGPT, open **Plugins → Add custom MCP server**,
choose **Tunnel**, select your tunnel and complete the connection. Workspace
permissions and feature availability apply. This requires separate OpenAI tunnel
setup; Fitro does not include the tunnel client or provide an HTTP endpoint.
See [OpenAI's connection guide](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt).

### Antigravity

In Antigravity IDE, open **MCP Servers → Manage MCP Servers → View raw config**.
Merge this into `mcp_config.json`:

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

Save and reload the server. Current Antigravity documentation places global config
at `~/.gemini/config/mcp_config.json` and workspace config at `.agents/mcp_config.json`.
Use your app's raw-config view to locate the file for your installed version.
See [Google's MCP setup guide](https://antigravity.google/docs/mcp?tab=ide).

### Codex

Paste this into `~/.codex/config.toml`, then save and reconnect Fitro or restart Codex:

```toml
[mcp_servers.fitro]
command = "uvx"
args = ["fitro-mcp@1.0.0"]
startup_timeout_sec = 60

[mcp_servers.fitro.env]
GARMIN_PERSONAL_API_KEY = "PASTE_YOUR_PERSONAL_API_KEY_HERE"
```

See the [official Codex MCP guide](https://developers.openai.com/codex/mcp).
If your launcher supplies the key from its environment, omit `[mcp_servers.fitro.env]` and
set `env_vars = ["GARMIN_PERSONAL_API_KEY"]` inside `[mcp_servers.fitro]` instead.

### Check the connection

Ask your connected assistant:

> Use Fitro to list the available activity types.

This tests authentication without retrieving personal health measurements.
For debug logs, add `"--debug"` after `"fitro-mcp@1.0.0"` in the argument list.
For a China-region account, set `FITRO_REGION` to `china` in your server environment.

## Sample Prompts

Use a day or a short date range. Ask the assistant to discover the right operation
and report unavailable measurements rather than guess.

**Daily summary**

> Use Fitro to show my steps and sleep for yesterday. Discover the operations you
> need first, and tell me if any data is unavailable.

**Recent activities**

> Find my five most recent running activities and summarize their distance and duration.

**Visualize steps**

> Use Fitro to fetch my daily steps for the last seven days. Visualize them as a
> bar chart with dates on the x-axis and steps on the y-axis. Show missing days as
> missing rather than zero, and include the source values in a table.

**Visualize sleep**

> Use Fitro to compare my sleep duration over the last seven days. Create a line
> chart in hours, leave gaps for unavailable nights, and summarize the pattern
> without making medical claims.

**Explore women's health**

> Use Fitro to show which women's health operations are available. Don't retrieve my data yet.

Charts are created by your assistant/client from the returned data. Fitro itself
does not render charts or expose a built-in visualization tool. If the client cannot
render a chart, ask for a table or a plotting script instead.

## Technical Details

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

### Troubleshooting and diagnostics

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

### Privacy and personal use

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

### Development and alternative installation

For code organization and extension contracts, see the
[code reference](docs/code-reference.md), [architecture](docs/architecture.md),
[contributor guide](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

#### Run from a checkout

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

#### Install with pip

If you prefer to manage a virtual environment instead of using `uvx`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install fitro-mcp==1.0.0
fitro-mcp --version
```

For an MCP client using this installation, set `command` to the absolute path of
that environment's `fitro-mcp` executable and omit the `uvx` package arguments.

#### Verify changes

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

#### Release automation

Stable `vMAJOR.MINOR.PATCH` tags trigger GitHub Actions to verify, publish to PyPI,
and create a GitHub Release with matching distribution files and checksums. See
[the publishing guide](docs/publishing.md) for tag creation, reruns and credentials.

[Source](https://github.com/phanijapps/fitro-mcp) ·
[PyPI](https://pypi.org/project/fitro-mcp/) ·
[Releases](https://github.com/phanijapps/fitro-mcp/releases) ·
[Changelog](CHANGELOG.md) ·
[Official API Swagger](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/)
