# Changelog

## Unreleased

- GitHub Actions tag-based PyPI publication and GitHub Releases, with immutable
  version checks, shared verification, exact registry assets and checksums.

## 1.0.0 — 2026-11-20

First stable release using the new **Fitro MCP** identity.

- Five read-only tools: Activity, Health (including women's health), Wellness,
  Profile and Discover, covering 28 documented Personal API operations.
- Progressive offline discovery with exact schemas and examples on demand.
- MCP guide/domain/operation resources, resource templates, completion,
  server instructions and structured results with diagnostic request IDs.
- Official API-key exchange, plain-text JWT response support, memory-only caching,
  synchronized renewal and a single retry after bearer rejection.
- Fixed verified HTTPS origins, strict input validation, timeouts, bounded response
  reads and sanitized failures.
- `--debug` with private, process-coordinated rotating diagnostics: 1 MB per file
  and three backups, excluding health data and credentials.
- Versioned PyPI installation and Codex TOML/CLI setup, simple prompts, contributor
  guidance, architecture/API notes, packaging smoke checks and security checks.

### Migration from the development checkout

The unreleased `stridebridge-mcp` / `stridebridge_mcp` names become `fitro-mcp` /
`fitro_mcp`. The Codex server entry is `fitro`. Configuration variables use `FITRO_`
instead of `STRIDGEBRIDGE_`; `GARMIN_PERSONAL_API_KEY` is unchanged. Resource URIs
use `fitro://`.

The requested `~/.starbridge/` directory stays in place. New logs are named
`fitro.log` through `fitro.log.3`; earlier development logs are left untouched.
The original one-tool-per-endpoint interface is replaced by domain tools with
`operation` and `parameters` arguments.
