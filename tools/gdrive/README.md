# Drive OAuth compatibility (Codex, 2026-09-13)

Preserves zcode's `@modelcontextprotocol/server-gdrive` **2025.1.14** read-only tool/resource handlers. Upstream: [archived Google Drive server](https://github.com/modelcontextprotocol/servers-archived/tree/main/src/gdrive), MIT; see LICENSE. This is not a new agent/tool design.

The installed upstream loaded access/refresh tokens into `new google.auth.OAuth2()` without the OAuth application's client ID and secret. It could initialize/list tools, but actual expired-token refresh returned HTTP400 `invalid_request`. Constructing the same client with the existing application's identity passes authentication. No credential replacement, file writes or scope expansion is needed.

`index.mjs` retains all upstream tool/resource handlers unchanged; only OAuth construction, explicit path resolution and sanitized startup errors differ. `oauth.mjs` validates the configured application/credentials and constructs a refresh-capable client. The legacy `../gdrive-mcp.cmd` entry now starts this fixed local version; it no longer downloads `@latest`. Existing Core tool qualification (`mcp__drive__search`) and confirmation rules are unchanged.

## Installation and checks

Run `npm ci --ignore-scripts --no-audit --no-fund` in this directory during development/package preparation, not at user startup. The lockfile pins transitive dependencies; `node_modules` must accompany a ready-to-run distribution (or be provisioned beforehand). Node itself still needs to be included by the portable packager.

`npm test` runs four offline OAuth-construction regressions without credentials or Google requests. An explicitly authorized authentication-only check is `node check-auth.mjs`, with `GDRIVE_OAUTH_PATH` and `GDRIVE_CREDENTIALS_PATH` set to the operator's files. It performs token refresh/introspection only, writes no credentials and reads no Drive content. Output is booleans only.

Keep credentials outside the delivered public archive. The CMD wrapper respects explicit path/proxy variables; its current machine-compatible proxy fallback is `127.0.0.1:7897`, not a portable network guarantee. Supply a suitable proxy/environment on a new machine. Do not launch `auth` unless the operator explicitly wants the interactive authorization flow.

Validation: original HTTP400 reproduced; corrected client with the same credentials passed token introspection and the existing `drive.readonly` scope check. Actual patched CMD initialization/listing returned the unchanged one-tool schema. Business-handler hash is `3a6f94d28991b52a6b4cba55521d3fe3bc14a93c4d71a3a7846035442daf5f59`. Offline regressions use synthetic credentials and make no remote requests. See the [public integration summary](../../docs/DELIVERY_STATUS.md); private account files and raw acceptance records are not published.
