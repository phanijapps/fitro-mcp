# Security

Never include a Personal API key, bearer token, health payload, request URL or raw
upstream error body in a public issue. Use
[GitHub private vulnerability reporting](https://github.com/phanijapps/fitro-mcp/security/advisories/new)
if the repository owner has enabled it. If private reporting is unavailable,
contact the repository owner privately before sharing sensitive details. Do not
open a public issue containing exploit credentials or personal data.

The server is intended for a single trusted local MCP client. It uses stdio only,
fixed verified HTTPS origins, no redirects, bounded reads and sanitized errors.
Ruff security rules, strict type checks, synthetic upstream tests and pip-audit
are required checks; they do not establish an absence of vulnerabilities.

Version 1.0.0 is the current stable release. Review dependency audit results before
publishing updates. API credentials and personal data are never persisted
by the server. Local diagnostics in `~/.starbridge/fitro.log` are allowlisted
to generic events, random request IDs, timings and status codes. `--debug` does not
relax redaction. Logs rotate at 1 MB with three private backups. Your MCP client controls storage and forwarding of tool results.
