# Code reference

This is a guide to contracts and ownership, not a generated list of every symbol.
Read [architecture.md](architecture.md) for the full request/data flow.

## Composition and lifecycle

`fitro_mcp.__main__.main()` parses `--version`/`--debug`, configures private local
logging, loads `Settings`, and runs `serve()`. Help/version exit without credentials.
Startup failures print fixed, sanitized messages to stderr. stdout carries MCP only.

`server.create_server(settings)` returns a new MCP SDK server and registers five
tools plus resource handlers. Its async lifespan owns exactly one
`PersonalAPIClient`, whose connection pool and cached token are closed/discarded
when the session stops. Importing the package performs no network or file I/O beyond
Python module loading. File logging starts only in the CLI setup.

The inner `call_tool` handler validates a domain envelope before resolving an
operation. It validates operation parameters before HTTP dispatch. The HTTP layer
also validates its inputs independently so direct Python use is safe. Every call
has a random request ID propagated through `ContextVar`, reset in `finally` so
concurrent calls do not borrow each other's identifiers.

## Settings

`config.Settings` is immutable. Its `api_key` is a Pydantic `SecretStr`, omitted
from representations. `from_env()` reads only supported variables and sanitizes
validation errors. Region chooses one of two fixed HTTPS origins; callers cannot
supply an arbitrary API host. Header control characters and whitespace are rejected
in credentials. The package does not load `.env` files automatically.

## Catalog and discovery

`catalog.Operation` models reviewed metadata: internal name, domain, GET path,
parameter schema, path parameter names and binary-response flag.
`prepare(arguments)` applies JSON Schema/format validation, rejects backwards date
ranges, percent-encodes path substitutions, and returns `(path, query_parameters)`.
It does not authenticate, log inputs or make a request.

`load_catalog()` reads the bundled `data/operations.json` using package resources,
so it works from wheels as well as editable checkouts.

`discovery.operation_id()` removes the internal `get_` prefix. `resolve()` enforces
that a public identifier belongs to the selected domain. `tool_schema()` builds the
compact domain contract; `discover()` either returns domain metadata, a paginated
summary, or one exact schema/example. Its keyword search stays local and bounded.
`describe()` generates only synthetic example values, never account-specific data.

`resources.register_resources()` delegates to those same catalog functions for
`fitro://guide`, domain indexes and operation contracts. Completion suggests public
names for URI-template arguments; it does not autocomplete tool parameters.
Resources require no upstream API call. Unknown URIs produce fixed errors.

## Authentication and HTTP

`authentication.parse_token_response(body)` returns `(token, lifetime_seconds)`.
Its result is sensitive. The parser accepts the observed raw compact JWT, a JSON
string or compatible JSON token envelope; it never logs, decodes JWT claims or
returns credentials through MCP. Malformed bodies produce a fixed `BridgeError`.

`PersonalAPIClient` accepts an optional `httpx.AsyncBaseTransport` for tests.
The production transport verifies TLS, ignores environment proxy configuration,
disables redirects, and uses a bounded pool and per-phase timeouts.

`_get_token(rejected=None)` holds an async lock across exchange/cache decisions.
The `rejected` token lets a concurrent caller reuse a replacement already obtained
by another request, avoiding redundant renewals. Cache deadlines use a monotonic
clock and a 60-second safety margin, capped at the FAQ's 24-hour lifetime.

`_request()` streams successful responses into a bounded buffer. Token bodies have
an additional 64 KiB cap. Error bodies are not read. Network/status failures become
safe `BridgeError` messages; nothing serializes HTTPX exceptions into MCP output.
The diagnostic HTTP timing describes response-header latency; the outer tool timing
covers the complete operation.

`execute()` validates arguments, obtains a bearer token, then runs one GET. Only a
401 triggers renewal/retry, once. Other HTTP failures and rate limits are reported
without automatic retry. ZIP downloads return bytes; other responses return JSON.
Always call `aclose()` if using the client directly outside the server lifespan.

## Results and diagnostics

Successful tools return `request_id` and `data`; execution data wraps `operation`
and `result`. Failures add a safe `error` and set MCP `isError`. `structuredContent`
and JSON text fallback carry the same envelope. No upstream response models are
claimed beyond the supported serialization contract.

`diagnostics.event()` accepts fixed event names and numeric metadata only.
`SafeFormatter` emits approved fields rather than formatting arbitrary log messages
or exceptions. Request IDs are generated UUID hex strings, unrelated to activity or
account identifiers. SDK/HTTP logs are excluded even in debug mode.

`PrivateRotatingHandler` reopens the current file under an interprocess file lock
before emitting. This observes rotations made by other clients and keeps active
and retained logs bounded. POSIX files are private, links are refused, and errors
never dump the original log record. The directory remains `~/.starbridge` by user
request; the release log name is `fitro.log`.

## Worked extension: another GET operation

1. Review the official Swagger path, parameters, formats, required flags and response
   media type. Record the review date. Do not invent an upstream endpoint.
2. Add one `operations.json` entry with a unique internal name and the appropriate
   domain. `path_parameters` must match the path placeholders. Close the input
   schema using `additionalProperties: false`.
3. Set `binary` only for the supported ZIP download contract; other media types need
   explicit serialization design. No generic HTTP methods or paths become inputs.
4. Add transport tests asserting the exact path/query and a synthetic response.
   Verify malformed inputs fail before authentication, and the operation cannot be
   selected through another domain.
5. Confirm discovery, resource documentation and domain tool enums include the new
   operation. Update the README/coverage counts and run all required checks.

The package's public configuration and MCP tool/result contracts are versioned.
Internal helper functions are documented for maintainers, not promised as a separate
stable Python SDK for third-party applications.
