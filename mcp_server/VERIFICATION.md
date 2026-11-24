# MCP verification — 24 November 2026

- Full Python suite: **142 passed** (107 existing tests plus 35 MCP tests).
- MCP suite: **35 passed**, with migrated temporary SQLite databases.
- Existing frontend suite: **13 passed**, across four files.
- Existing production build: strict TypeScript checking and Vite build passed.
- Runtime protocol test: the official SDK `ClientSession` initialized over real
  loopback Streamable HTTP, listed all seven tools, created a recipe, and read it
  back. No personal database was used.
- HTTP tests verified authentication before dispatch, Host/Origin/Fetch Metadata
  restrictions, request size limits, structured validation errors and tool discovery.
- Transaction tests covered invalid batches, existing/repeated titles, concurrent
  duplicate additions and rollback after an injected commit failure.
- Web/MCP interoperability tests verified shared persistence, retained personal
  feedback/history, original fractional quantities/timers and scaled shopping totals.
- SDK tested: official `mcp` 1.30.0; Python 3.12.13, Windows. Frontend checks used
  the installed Node 26.12.0 runtime directly because the default nvm shim had no
  active version. Tests used workspace-local temporary directories because the
  sandbox restricted the OS pytest temp directory. Frontend verification required
  running outside that sandbox so esbuild could resolve the project configuration.
- One third-party test warning: Starlette deprecates its httpx-backed TestClient;
  the SDK's actual httpx Streamable HTTP client test passes.

No existing application source, migrations, personal data, credentials or deployed
services were changed. No commit was created. Pi installation, systemd/reboot
behavior, Secure MCP Tunnel, OAuth gateway deployment and a real ChatGPT custom
plugin connection remain environment/account checks; they are documented, not
claimed as tested. The supplied service is not installed or started automatically.
