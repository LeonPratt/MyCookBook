# MyCookBook MCP service

This optional service lets an authorized MCP client retrieve, create and update
recipes in the **same database** as the web app. All integration files live in
`mcp_server/`. Run commands from the repository root. The web server does not need
to be running for MCP database access.

## Architecture and data contract

- Official Python MCP SDK **v1**, using `mcp.server.fastmcp.FastMCP`; the `<2`
  dependency bound is intentional because SDK v2 changes this API. No separate
  third-party FastMCP package is needed.
- Streamable HTTP at `http://127.0.0.1:8001/mcp`, stateless JSON responses, one
  Uvicorn process. Python 3.11+; compatible with the documented Pi 3's Python 3.13
  and ARM64 environment. No Node process is required to run the service.
- `cookbook.create_app()` loads existing `COOKBOOK_DATABASE_URL`,
  `COOKBOOK_DATA_DIR` and upload configuration. Never point MCP at a new database
  when intending to edit the household collection.
- `cookbook.schemas.RecipeInput` generates both tool input schemas and
  `get_recipe_schema`. Its nested ingredient and step models validate all writes.
  `transfer_records` and `import_records` handle additions; the existing
  `filtered_recipes` and `serialize` functions handle search and retrieval.
- There are no new tables or migrations and no production `create_all` call.
  Initialize/upgrade the existing app through its normal migration workflow.
- Recipe quantities remain numeric original quantities (or null); ingredient
  groups, optional flags, preparation notes, equipment alternatives, source,
  tags, image references and instruction timers are retained. Scaling continues
  to happen in the existing frontend. Feedback and history are separate.
- Images must already have been uploaded through the cookbook UI/API. Only its
  generated `/uploads/<32 lowercase hex characters>.jpg|png|webp` references
  are accepted by the existing validator. MCP cannot fetch remote images, upload
  images, set arbitrary filesystem paths, or bypass the image decoder allowlist.

The existing Flask app has no login/accounts: it is designed for one trusted
household LAN. Its Host/Origin/Fetch Metadata protections are unchanged. MCP is
an additional, explicitly authenticated access boundary; its token grants
read/write access to that household. No API credentials or LLM settings are tools.

## Install and run locally

Use the existing development virtual environment, or a new environment with the
same production dependencies:

```sh
python -m pip install -r mcp_server/requirements.txt
```

On this Windows checkout, substitute `.venv-dev/Scripts/python.exe` for `python`.
On the Pi use the tested release's `.venv/bin/python`. Do not copy virtual
environments between architectures. Keep dependency installation separate from
the running release; test a staged release before switching `current`.

Generate a secret locally, then store it privately in your existing `.env` or
service environment. Do not paste it into chat or commit it:

```sh
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the **variable names** from [`.env.example`](.env.example) into that private
environment. Set `MCP_API_TOKEN` to the generated secret. Retain the existing
`COOKBOOK_DATABASE_URL` and `COOKBOOK_DATA_DIR` values. Start:

```sh
python -m mcp_server
```

The process refuses a missing/short token or a non-loopback bind address. It
never migrates or initializes databases automatically. Existing installations
need no schema upgrade for this feature.

| Variable | Default | Purpose |
| --- | --- | --- |
| `MCP_API_TOKEN` | required | At least 32 ASCII characters without whitespace; bearer authentication on every HTTP request |
| `MCP_HOST` | `127.0.0.1` | Loopback only (`127.0.0.1`, `localhost`, `::1`) |
| `MCP_PORT` | `8001` | Local listening port |
| `MCP_RECIPE_BASE_URL` | empty | Web app base URL used for `/#recipe/<id>` links; URLs are null if omitted |
| `MCP_ALLOWED_HOSTS` | empty | Extra exact HTTP Host values, comma separated, for a proxy; include port if present |
| `MCP_ALLOWED_ORIGINS` | empty | Explicit browser origins; normally unnecessary; wildcards rejected |

Loopback Hosts with the configured port are accepted automatically. No forwarded
headers are trusted, access logging is disabled, request bodies are limited to
2 MiB and bulk additions are limited to 100 recipes. Tokens are compared in
constant time, including on discovery and read requests. No CORS allowance is
enabled. Never put a token in a URL/query string. To rotate it, replace the private
environment value, restart this service, and update the client's credential.

## Tools

| Tool | Arguments | Result/behavior |
| --- | --- | --- |
| `get_recipe_schema` | none | Schema version and live Pydantic JSON Schema |
| `add_recipe` | `recipe: RecipeInput` | Save a new, uniquely titled recipe |
| `add_recipes` | `recipes: list[RecipeInput]` | 1–100 new recipes, one transaction |
| `get_recipe` | `recipe_id` | Full original recipe, feedback, history and `updated_at` |
| `search_recipes` | `query`, `ingredient`, `cuisine`, `category`, `limit`, `offset` | Existing web search semantics; query includes title, description, ingredients, cuisine, category and tags |
| `list_recipes` | `limit=20`, `offset=0` | Alphabetical page; total and next offset |
| `update_recipe` | `recipe_id`, `recipe: RecipeInput`, optional `expected_updated_at` | Replace editable content while retaining personal data/history |

IDs are positive integers. Page sizes are 1–100 and offsets are nonnegative.
There is no deletion tool. Read tools are annotated read-only/idempotent;
additions are non-destructive/non-idempotent; updates are destructive/idempotent
because they replace content. All tools declare a closed household context.

Write results contain `success`, `recipe_id`, `title`, and `url`; bulk results
contain `success`, `imported`, and a `recipes` list of those summaries in input
order. Results are both JSON text and MCP `structuredContent`.

```json
{
  "recipe": {
    "title": "Lemon rice",
    "servings": 2,
    "ingredients": [
      {"name": "rice", "quantity": 150, "unit": "g", "group": "Main"},
      {"name": "lemon", "quantity": 0.5},
      {"name": "salt", "quantity": null}
    ],
    "instructions": [{"text": "Simmer until tender.", "timer_seconds": 600}]
  }
}
```

Use this as the `add_recipe` arguments object in Inspector. Ask the schema tool
for all other fields. Unknown fields, non-finite/negative/oversized quantities,
invalid portions, unsafe image paths and invalid timers are rejected.

Titles are compared with the existing importer normalization (case-insensitive,
surrounding whitespace ignored). An existing title or a duplicate within a batch
rejects the **whole operation**, rather than silently skipping or replacing it.
Search first, then update by ID if intended. An invalid batch never saves its valid
prefix. SQLite `BEGIN IMMEDIATE` serializes MCP duplicate checks and writes; busy
or failed database operations roll back and return an error. The existing web UI
can still intentionally create duplicate titles; this integration does not add a
global uniqueness constraint or change existing web behavior.

Updates accept **full recipe content**, not a partial patch. Get the recipe,
retain all fields from `RecipeInput`, change only requested fields, and submit
that content. Do not send response-only `id`, `personal`, `history`, or derived
timestamps/counts in `recipe`. Omitted optional fields reset to their schema
defaults. Pass the retrieved `updated_at` as `expected_updated_at` to detect a
concurrent edit. Personal feedback, selected portions and history are untouched.

Domain and validation failures return `isError: true` with:

```json
{"success": false, "error": {"code": "duplicate_recipe", "message": "...", "details": {"index": 0, "recipe_id": 7}}}
```

Other codes include `validation_error` (field-level details), `not_found`,
`conflict`, `database_error`, `internal_error`, and `tool_error`. Authentication
fails before dispatch with HTTP 401 and a Bearer challenge. Error responses do
not include raw inputs, SQL, exception traces, connection strings or tokens.
After a connection drops during a write, search/get before retrying: the commit
may already have succeeded even if its response was lost.

Audit logger `mycookbook.mcp.audit` records operation, success/failure code and
successful recipe IDs. It does not log tokens, titles, ingredients, personal
notes or request bodies. This shared household token is not a per-user identity.
Do not enable HTTP/debug payload logging on a proxy or tunnel carrying secrets.

## MCP Inspector

On a development machine with Node installed:

```sh
npx @modelcontextprotocol/inspector@latest
```

Choose **Streamable HTTP**, URL `http://127.0.0.1:8001/mcp`, and add
`Authorization: Bearer <your private MCP_API_TOKEN>` in the request authentication
headers (enter it locally). Use Inspector's proxy connection. If using its direct
browser mode, it may require CORS support; use the proxy instead. For a local
browser-origin rejection, only allow the exact trusted Inspector origin rather
than introducing wildcards. Inspect the seven tools, then call schema, add,
get, search, list and update against temporary data. Disconnect and repeat
without the token to confirm 401. Do not run write experiments on personal data.

For inspection on a laptop while the service remains on the Pi, use an SSH
local forward (`ssh -L 8001:127.0.0.1:8001 recipe-pi`) and keep the Pi listener
on loopback. This does not make localhost directly reachable from ChatGPT.

## Raspberry Pi 3 service

Use the existing versioned Git release layout described in `DEPLOYMENT.md`.
Stage a new checkout containing `mcp_server/`, install its MCP requirements into
that release's environment, and run the checks below before switching releases.
The older `scripts.package_release` archive allowlist does **not** include this
optional directory: use the documented Git checkout release workflow for MCP.
Keep shared data, environment and backups outside the checkout. Budget additional
SD space for the SDK dependencies and a second Python process; do not delete
old releases automatically. Pi hardware/resource measurements remain to be made.

Privately add the MCP variables to
`/home/leon/apps/mycookbook/shared/.env` (mode 600). Review the supplied
[`mycookbook-mcp.service`](mycookbook-mcp.service); it uses the existing `leon`
account, `current` release, and shared environment/database. It grants writes
only to `shared/`, starts at boot, and restarts on failure. Adapt user/paths for
other installations. A separate service is intentional; no Gunicorn worker or
frontend changes are needed.

After staging/testing and the normal administrator approval for service changes:

```sh
sudo systemd-analyze verify /home/leon/apps/mycookbook/current/mcp_server/mycookbook-mcp.service
sudo install -m 0644 /home/leon/apps/mycookbook/current/mcp_server/mycookbook-mcp.service /etc/systemd/system/mycookbook-mcp.service
sudo systemctl daemon-reload
sudo systemctl enable --now mycookbook-mcp.service
systemctl is-active mycookbook-mcp.service
systemctl is-enabled mycookbook-mcp.service
journalctl -u mycookbook-mcp.service -n 50 --no-pager
```

Inspect/back up an existing unit before replacement. The service does not touch
the web unit. A request without credentials to `/mcp` should return 401; verify
authenticated initialization and schema discovery through Inspector. Confirm
port 8001 listens only on loopback with `ss -ltn`. Reboot verification requires
the owner's approval because the Pi runs other services. Preserve a database/photo
backup using the existing scripts before first use. Roll back by stopping this
MCP service and selecting the prior tested release; no MCP schema migration exists.

## Secure MCP Tunnel and ChatGPT

OpenAI documents Secure MCP Tunnel as an outbound connection for private MCP
servers, including HTTP targets. It fits this loopback `/mcp` transport without
opening a router port. Setup needs a tunnel ID, a runtime credential, the correct
workspace association and a running client. Start with the current client's help
and point its HTTP target at `http://127.0.0.1:8001/mcp`; use `doctor` to check the
profile before running it. Keep its OpenAI runtime credential separate from this
server's `MCP_API_TOKEN`. Confirm server-side Bearer authentication is forwarded
or injected using the installed client's supported configuration. Never disable
MCP authentication to fix discovery. Verify ARM64 binary availability/runtime
support on this Pi before installation. This transport compatibility is inferred
from the documented HTTP support; an actual account/tunnel connection has not
been tested. [Official tunnel setup](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

In ChatGPT Plugins, add a custom MCP server, select **Tunnel** and the configured
tunnel, or supply a public HTTPS MCP URL with OAuth as below. Configure
authentication, create the plugin, review all seven tools, then select it in a new
conversation. Try schema discovery and recipe search before authorizing writes.
After tool names, descriptions, schemas, annotations or authentication change,
restart the service, open the plugin connection, select **Refresh**, confirm the
new descriptors, and retest in a new conversation. Account/workspace policy may
restrict this flow. [Official connection and refresh instructions](https://developers.openai.com/plugins/deploy/connect-chatgpt).

Neither the tunnel nor the plugin is provisioned by this repository. A live
ChatGPT connection requires the owner's account and credentials. If the available
ChatGPT/tunnel auth interface cannot send this service's bearer credential, use
an MCP-aware OAuth gateway; do not select anonymous authentication against a
public proxy. Tool annotations describe behavior and are not access controls.

## Public HTTPS and OAuth

The included local token verifier is **not an OAuth authorization server**.
For a public deployment, use an MCP-aware OAuth 2.1 gateway/resource server with
an identity provider. It must publish protected-resource metadata and a 401
`WWW-Authenticate` discovery challenge, support authorization code + PKCE and
the MCP `resource` audience, and validate issuer, audience, expiry and scopes on
every request. Configure client registration/identification supported by ChatGPT
(CIMD, DCR or a predefined client). Scope access to this household; only tokens
authorized to write recipes may reach write calls. Merely checking that a Bearer
header exists or trusting a user-supplied identity header is insufficient.
[Official MCP OAuth guidance](https://developers.openai.com/plugins/build/auth).

Terminate HTTPS at that gateway; forward only authorized MCP requests over
loopback to this service. Strip incoming Authorization/forwarded identity headers
and inject `MCP_API_TOKEN` from a private **environment variable** on the upstream
hop. Store OAuth client secrets in the gateway's private environment as well.
Keep the backend port inaccessible externally, set an exact allowed Host if the
gateway preserves a public hostname, and leave forwarded-header trust disabled.
The gateway owns OAuth discovery routes; this service's 401 is only local bearer
auth. It must authorize every MCP method/batch, including tool discovery and
write tool calls, rather than acting as a generic unauthenticated HTTP proxy.
Validate unauthorized/expired/wrong-audience/read-only-token failures end to end
before any public use. A concrete gateway/provider must be chosen and configured
before public deployment; this change does not install one or expose a port.

## Tests and verification

Install the optional SDK requirements above plus the existing development
requirements, then run:

```sh
python -m pytest -q mcp_server/tests
python -m pytest -q
cd frontend
npm test
npm run build
```

Tests use migrated temporary SQLite databases, including real SDK client calls
over local Streamable HTTP, authentication/Host/Origin/body limits, schema
rejection, search/pagination, concurrent duplicate additions, transactional bulk
imports, failed-commit rollback, secret-safe errors/audit logs, preservation of
feedback/history, and web shopping scaling after MCP updates. No personal data
or running deployment is used. For a sandbox that restricts the OS temp directory,
pass a new workspace-local `--basetemp .tmp/<unique-test-run>` directory to pytest.
The optional MCP tests skip collection when its SDK dependency is not installed;
the existing application does not require MCP.
