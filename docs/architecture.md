# Architecture and extension points

The console composes validated settings, a low-level official MCP SDK server, an
operation catalog, and an async HTTP client. MCP startup creates a pooled HTTP
client; shutdown closes it. Five tools are public: `discover`, `activity`, `health`,
`wellness`, `profile`. All 28 reviewed GET operations remain internal adapters.
Women's health belongs to Health; sleep/nutrition belong to Wellness.

`MCP client → domain tool → validated operation → HTTP client → regional API`

`discover` browses four domain summaries, paginated operation summaries, or a single
exact contract. Public operation identifiers omit the old `get_` prefix; internal
endpoint names remain stable. Each domain tool advertises a small operation enum
and a `parameters` object. The complete operation schema is retrieved only when
needed and is always enforced server-side before network access. No raw URLs,
methods, headers or endpoint paths are accepted from tool callers.

The source was OpenAPI 3.0.1, API version 1.0.0, embedded in Garmin's Swagger page
on 2026-11-20. `data/operations.json` preserves path/query names, types, formats,
required flags and descriptions, and assigns every operation exactly one domain.
Local policy adds positive activity IDs, a nonnegative search offset, and search
limits 1–1000. Response DTOs remain upstream JSON; the bridge supplies a stable
structured envelope (`request_id`, `data`, optional `error`) and a JSON text fallback.
Errors do not echo validation inputs or raw upstream bodies. Downloads are bounded
base64 ZIP data; neither results nor credentials are persisted.

Resources expose the offline guide, four domain indexes and operation contracts.
Domain and operation URI templates support context-aware argument completion.
The same discovery functions drive resource reads and tools, preventing drift.
Resource discovery does not depend on authentication, API availability or a model.
There are no dynamic tool-list changes, prompt handlers or MCP log notifications.
The `discover` fallback supports hosts that do not surface resources to models.

To add or update an operation:

1. Compare the official Swagger contract and record the review date.
2. Edit `data/operations.json` with its domain, stable unique internal name, path,
   path parameters, description, binary flag and closed input schema.
3. Add schema and path/query tests. Verify public identifiers remain unique within
   the domain and cross-domain execution remains impossible.
4. Update README coverage, discovery/resource tests, and verification records.

Keep protocol serialization in `server.py`, discovery contracts in `discovery.py`,
resource handlers in `resources.py`, HTTP/token lifecycle in `client.py`, token
parsing in `authentication.py`, and endpoint binding
in `catalog.py`. `PersonalAPIClient` accepts `httpx.AsyncBaseTransport` for isolated
tests; `create_server(settings)` gives each instance its own client and token cache.
There are no module-level network requests or mutable global API clients.

`diagnostics.py` owns all local log output. The CLI enables warnings/errors by
default, with `--debug` adding generic events. A context variable propagates a random
request ID into HTTP/token events without recording domain names, URLs, arguments,
health values or exception strings. Its formatter serializes only approved fields;
third-party logging is excluded. Rotation is 1,000,000 bytes with three backups in
`~/.starbridge`, with private POSIX permissions, link checks and an interprocess lock. Each event
reopens the current file under that lock so simultaneous clients observe rotation.
Logging failures
report fixed messages, never dump records or tracebacks.

The current scope is one user's local stdio process. Remote serving, multi-user
identity, storage and writes require separate design. HTTP timeouts apply to network
phases; cancellation propagates through async operations. Response limits bound each
call, not aggregate concurrent memory. Data pagination remains explicit; oversize
responses fail rather than silently truncate. Returned activity text is untrusted
data and should not be treated as instructions by a client.
