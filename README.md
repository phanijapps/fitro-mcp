# Fitro MCP

Your fitness and wellness data, available to an MCP-compatible assistant through
**five focused tools**: Activity, Health (including women's health), Wellness,
Profile, and Discover. Uses the official Garmin Connect Personal API, with all
28 reviewed read-only operations available through progressive discovery.

**Version 1.0.0 · Python 3.11–3.14 · MIT · Local stdio MCP**

[Source](https://github.com/phanijapps/fitro-mcp) ·
[PyPI](https://pypi.org/project/fitro-mcp/) ·
[Changelog](https://github.com/phanijapps/fitro-mcp/blob/main/CHANGELOG.md)

## Try a simple prompt

After connecting Fitro to Codex, ask:

> Use Fitro to show my steps and sleep for yesterday. Discover the operations you
> need first, and tell me if any data is unavailable.

For a connection check that does not request personal health data:

> Use Fitro to list the available activity types.

Other examples: “Find my five most recent running activities,” or “Compare my
sleep over the last seven days.” Fitro retrieves data; your assistant writes the
explanation. Missing measurements should be reported as unavailable.

## Install

You need Python 3.11+, [uv](https://docs.astral.sh/uv/getting-started/installation/),
and a **Garmin Connect Personal API key**. A Garmin login/password alone is not
enough. Create your key using the official
[Personal API key setup page](https://developer.garmin.com/gc-developer-program/personal/personal-api/).
Sign in to Garmin Connect, open Personal API Key, select **Create Key**, accept
the terms, choose an expiry and save the key when it is shown. Fitro exchanges
that key for a bearer token automatically.

Run the versioned PyPI package without managing an environment:

```bash
uvx fitro-mcp@1.0.0 --version
```

Or install with pip inside a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install fitro-mcp==1.0.0
fitro-mcp --version
```

Fitro runs as an MCP stdio process. Starting it without a client waits for protocol
messages on stdin; it does not open a web page or interactive shell. Linux is tested.
macOS uses the same POSIX file-permission model but has not been tested locally.
Native Windows is not supported in 1.0.0; use WSL for a Linux environment.

## Add to Codex

Add this block to `~/.codex/config.toml` (or edit an existing `fitro` entry):

```toml
[mcp_servers.fitro]
command = "uvx"
args = ["fitro-mcp@1.0.0"]
startup_timeout_sec = 60

[mcp_servers.fitro.env]
GARMIN_PERSONAL_API_KEY = "PASTE_YOUR_PERSONAL_API_KEY_HERE"
```

Replace the placeholder locally. Keep the key out of chat and source control.
Global is the default region. For China-region accounts, add
`FITRO_REGION = "china"` under the environment table. For debug logging, use
`args = ["fitro-mcp@1.0.0", "--debug"]`.

Alternatively, register a placeholder with the Codex CLI, then edit the key in the
configuration file:

```bash
codex mcp add fitro --env GARMIN_PERSONAL_API_KEY=PASTE_YOUR_PERSONAL_API_KEY_HERE -- uvx fitro-mcp@1.0.0
codex mcp list
```

If your Codex launcher supplies the key from its environment, use the following
instead of the `[mcp_servers.fitro.env]` table:

```toml
# Inside [mcp_servers.fitro]
env_vars = ["GARMIN_PERSONAL_API_KEY"]
```

Do not configure both approaches with a placeholder that overrides the real key.
If `uvx` is not on your launcher's PATH, set `command` to its absolute path. Allow
extra startup time for the initial package download. Restart Codex or reconnect its
MCP server after changing configuration; verify Fitro is connected, then try the
prompt above. See the [official Codex MCP guide](https://developers.openai.com/codex/mcp).

### Run from this checkout

```bash
uv sync --locked
uv run fitro-mcp --version
```

For Codex, replace the PyPI entry's command and arguments with:

```toml
[mcp_servers.fitro]
command = "uv"
args = ["--directory", "/absolute/path/to/gc-gather-mcp", "run", "--locked", "fitro-mcp"]
startup_timeout_sec = 60

[mcp_servers.fitro.env]
GARMIN_PERSONAL_API_KEY = "PASTE_YOUR_PERSONAL_API_KEY_HERE"
```

A direct local run can take the key from your shell. Bash example:

```bash
read -rsp 'Personal API key: ' GARMIN_PERSONAL_API_KEY; echo
export GARMIN_PERSONAL_API_KEY
uv run fitro-mcp
```

No `.env` file is loaded automatically. Keys are never accepted as command-line
arguments. Store client configuration with user-only permissions, such as `0600`
on POSIX systems.

### Other MCP clients

Clients using the `mcpServers` JSON format can use:

```json
{
  "mcpServers": {
    "fitro": {
      "command": "uvx",
      "args": ["fitro-mcp@1.0.0"],
      "env": {"GARMIN_PERSONAL_API_KEY": "PASTE_YOUR_PERSONAL_API_KEY_HERE"}
    }
  }
}
```

## What Fitro provides

- Five domain/discovery tools with about 77% smaller advertised definitions than
  the original 28-tool interface (serialized JSON size, not a model token benchmark).
- Offline documentation resources, URI templates and resource argument completion.
- Validated input schemas, bounded responses, explicit pagination and structured errors.
- API-key exchange for a bearer token, memory-only caching and one renewal after a 401.
- Private rotating diagnostics with `--debug`; stdout is reserved for MCP.
- Typed modular Python code, uv lockfile, Ruff security rules, strict mypy,
  synthetic tests, dependency auditing, package smoke checks and CI.

Live token exchange and activity-types retrieval have been verified on the global
region. Individual health endpoints and China-region authentication are not fully
verified live. See [authentication](docs/authentication.md) and
[verification](docs/verification.md) for the precise scope.

**Independent project. Not affiliated with, endorsed by, or sponsored by Garmin.**
Garmin and Garmin Connect are trademarks of Garmin Ltd. or its subsidiaries.
The [Personal API FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/)
limits the Personal API to an individual's own data and excludes commercial
applications serving multiple users. Installing this MIT-licensed client does not
grant rights to upstream services. The Fitro name has not received trademark clearance.

## Domain tools and discovery

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

## Configuration

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

## Private diagnostics

The region defaults to **global**. For debugging, append `--debug` after the server
command in your MCP client configuration:

```json
{
  "mcpServers": {
    "fitro": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/gc-gather-mcp", "run", "--locked", "fitro-mcp", "--debug"],
      "env": {
        "GARMIN_PERSONAL_API_KEY": "YOUR_PERSONAL_API_KEY"
      }
    }
  }
}
```

The PyPI equivalent is `"command": "uvx"` with
`"args": ["fitro-mcp", "--debug"]`. There is no log-level environment setting.

Logs go to **`~/.starbridge/fitro.log`**, using the requested `.starbridge`
directory spelling. The active file rotates before reaching **1,000,000 bytes**;
three backups (`fitro.log.1` through `.3`) are retained. Each file is at most
1 MB, for approximately 4 MB total. An additional private lock file coordinates
rotation across simultaneous clients. Default verbosity is warnings/errors; `--debug`
adds fixed diagnostic events. On POSIX systems the directory is `0700` and files
are `0600`; pre-existing symlinks and hard-linked files are refused.

Logs contain only timestamps, severity, fixed generic event names, random diagnostic
request IDs, HTTP status codes and durations. No health payloads, parameter values,
queried dates, activity IDs, domain/operation names, URLs, headers, keys, tokens or exception
text are logged. Third-party SDK/HTTP log output is excluded. Diagnostics remain
local and are not forwarded as MCP logging notifications. stdout remains MCP-only;
a logging initialization/write failure reports a fixed message on stderr.

Match a failed tool result's `request_id` to the local log when troubleshooting.
Debug output deliberately cannot show upstream response bodies or detailed payloads.

## Develop and verify

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run pip-audit
uv build
uv run twine check dist/*
```

Tests never need an API key or live account. See [AGENTS.md](AGENTS.md) for the repo
map and definition of done, [architecture](docs/architecture.md) for extension
points, and [publishing](docs/publishing.md) for release steps. See
[verification results](docs/verification.md) for the checks run.

Source: [official Swagger page](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/).
The bundled catalog contains reviewed operation metadata, not a runtime dependency
on the documentation website. API responses are returned as provided, with no
medical interpretation. Code is [MIT licensed](LICENSE).
