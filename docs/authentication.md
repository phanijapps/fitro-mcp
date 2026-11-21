# Authentication contract and verification

Official references reviewed 2026-11-20:

- https://developer.garmin.com/gc-developer-program/personal/personal-api/
- https://developer.garmin.com/gc-developer-program/personal/personal-faq/
- https://developer.garmin.com/gc-developer-program/personal/swagger-docs/

Before every data request, the client obtains or reuses a cached access token.
The exchange is POST
`/personalapitoken-service/personal-api/personal-api-key/token` with header
`Authorization: ApiKey <key>`. Brackets in Garmin's example denote a placeholder;
this client sends the actual key without brackets. Data calls then use
`Authorization: Bearer <token>` on the same regional origin. Listing tools,
discovering operations and reading documentation resources do not require an
exchange because they do not access account data.

## Observed response and compatibility

A manual global-region exchange returned HTTP 200 with a **plain-text compact JWT**,
not a JSON object. The previous JSON-only parser incorrectly rejected that successful
response. The parser now recognizes the plain JWT, allowing surrounding response
whitespace, and uses it directly as the bearer token.

For compatibility, the parser also accepts a JSON string or a JSON object containing
`access_token` or `accessToken`, with optional `expires_in` or `expiresIn` in seconds.
These JSON variants are tested synthetic formats, not observed upstream responses.
Non-JSON bodies must match compact JWT syntax; HTML, arbitrary plaintext and header
injection are rejected. All returned tokens must satisfy the bearer character set.
Parsing errors use a fixed message without echoing the response.

The FAQ says tokens last 24 hours or until key expiration, whichever comes first;
refresh tokens are not supported. If no explicit lifetime is returned, the cache
uses 86400 seconds, expiring 60 seconds early. JWT claims are neither decoded nor
trusted to derive lifetime. JWT syntax recognition is not signature verification;
the credential comes from the verified HTTPS endpoint and is checked by the API.

A data GET receiving HTTP 401 renews the token once and retries once. A lock avoids
concurrent exchanges, including concurrent rejection of the same cached token.
Closing the client drops its token reference; Python cannot guarantee secure memory
erasure. No credential retrieval tools exist. Keys/tokens remain in memory during
execution, are never logged, and are never returned through MCP.

## Verification scope

A manual test used the locally configured key to complete MCP initialization and
call `activity` with `operation: "activity_types"` and empty `parameters`. The token
exchange and authenticated GET succeeded. Only the success status was reported;
no credentials, response bodies or personal health data were saved as fixtures.

Automated tests remain entirely synthetic and verify the POST-before-GET sequence,
ApiKey/Bearer headers, plain JWT and JSON parsing, token caching, expiry, one-time
renewal, malformed-response rejection and log privacy. China-region authentication
and individual health/activity payloads have not been verified live.

If troubleshooting another response format, report only HTTP status and structural
field names; never paste the response body or token. Restart the MCP process after
updating code so it loads the corrected parser.
