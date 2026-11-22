# MyCookBook

A personal, self-hosted recipe manager for a Raspberry Pi 5 and a trusted local network. Flask serves a responsive React application and stores recipes, feedback, cooking history, shopping lists and preferences in SQLite. All core functionality works offline. Fonts, icons and illustrations are bundled locally; uploaded photos are optional.

For the inspected Raspberry Pi 3 deployment and future update commands, see [DEPLOYMENT.md](DEPLOYMENT.md). Its frontend is built locally, and production Python dependencies exclude development tools.

Features include full recipe editing, search across titles/descriptions/ingredients/cuisine/category/tags, filters and six sort orders, favourites and independent feedback, instant portion scaling, cooking mode with checklists/timers, meal history, pantry matching, explainable suggestions, shopping aggregation, JSON/text import with review, exports and backups. The optional LLM importer is disabled unless configured.

## Quick start

Requires Python 3.11+ and Node.js 22+ with npm. Node is needed only for frontend development/building, not production serving. Tested here with Python 3.12 and Node 26 on Windows.

Linux/macOS:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m flask --app wsgi db upgrade
python -m flask --app wsgi demo
cd frontend
npm ci
npm run build
cd ..
gunicorn --config gunicorn.conf.py wsgi:app
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m flask --app wsgi db upgrade
.\.venv\Scripts\python.exe -m flask --app wsgi demo
Set-Location frontend
npm ci
npm run build
Set-Location ..
.\.venv\Scripts\python.exe -m waitress --listen=127.0.0.1:5432 wsgi:app
```

Visit `http://localhost:5432`. After installation, `python -m scripts.serve` starts the platform's production server (Waitress on Windows, Gunicorn on Linux), loading host/port from `.env` and defaulting to loopback if no host is configured. For phone access on Windows use `--listen=0.0.0.0:5432` with Waitress, or set `COOKBOOK_HOST=0.0.0.0` for the helper, then open `http://<computer-LAN-address>:5432` on the same Wi-Fi. Firewall rules may need configuration by the administrator. This repository's development session uses `.venv-dev`; the commands above use the conventional `.venv` for a fresh installation.

For frontend hot reload, run `python -m flask --app wsgi run --host 127.0.0.1 --port 5432` in one terminal, then `npm run dev` inside `frontend` in another. Vite proxies `/api` and `/uploads` to Flask. Use the printed Vite URL. No debug interface is enabled by default.

## Structure and architecture

```text
cookbook/          Flask app, models, schemas, API, business services, demo recipes
frontend/src/      Typed React views, reusable controls, CSS/Tailwind design system
migrations/        Alembic versioned database migrations
tests/             Pytest API, import, quantities, security and persistence checks
scripts/           SQLite/photo backup and restore utilities
deploy/            systemd service example
docs/              API and JSON format documentation
instance/          Runtime SQLite database and uploaded images (ignored by Git)
```

Flask + SQLAlchemy + Flask-Migrate/Alembic + Pydantic form the backend. SQLite stores structured recipe content in a JSON column with an independently validated personal-data column. History is relational and cascades when a recipe is deleted. Shopping items and settings have separate tables. Reassign JSON fields on updates. A small household collection uses deterministic in-process filtering; FTS is not needed initially. This favors simplicity over a search-service dependency.

React 19 + TypeScript + Vite + Tailwind + Lucide form the frontend. Hash navigation keeps direct recipe links compatible with static serving. The custom local component system supports accessible labels, keyboard focus, dialogs and reduced motion. Recipe cards use decorative local plate illustrations until a photo is uploaded.

## Environment

Copy `.env.example` to `.env`; never commit secrets. Flask loads it on startup. For Gunicorn, the bind configuration is read before the app loads `.env`, so export host/port in your shell or use systemd's `EnvironmentFile` (as the supplied service does).

| Variable | Default | Meaning |
| --- | --- | --- |
| `COOKBOOK_DATABASE_URL` | `sqlite:///cookbook.db` | SQLAlchemy URL; relative SQLite paths resolve inside the data directory |
| `COOKBOOK_DATA_DIR` | `instance` | Absolute or repository-relative directory for runtime files |
| `COOKBOOK_HOST` | `0.0.0.0` | Gunicorn bind address |
| `COOKBOOK_PORT` | `5432` | Gunicorn port |
| `COOKBOOK_WORKERS` | `1` | Gunicorn worker processes; keep at one on the Pi 3 |
| `COOKBOOK_THREADS` | `2` | Threads per Gunicorn worker |
| `COOKBOOK_MAX_UPLOAD_MB` | `8` | Request/upload limit, including JSON imports |
| `COOKBOOK_ALLOWED_HOSTS` | empty | Extra exact hostnames, comma separated; localhost and private LAN IP literals are accepted automatically |
| `LLM_API_URL` | empty | Optional OpenAI-compatible base URL, including `/v1` if required |
| `LLM_MODEL` | empty | Optional endpoint model name |
| `LLM_API_KEY` | empty | Optional server-only credential |

The LLM importer POSTs to `<LLM_API_URL>/chat/completions`. Example local base: `http://127.0.0.1:11434/v1`; specify an installed model. It validates the extracted object and opens the normal editor before saving. Text is sent only when the user chooses the configured LLM option. The regular parser makes no network calls.

## Raspberry Pi 5 deployment

Use a 64-bit Raspberry Pi OS with Python 3.11+ and Node 22+ for the initial build. Install Python venv, pip and compiler packages if needed:

```sh
sudo apt update
sudo apt install python3-venv python3-pip build-essential libjpeg-dev zlib1g-dev
sudo useradd --system --home /opt/mycookbook --shell /usr/sbin/nologin cookbook
sudo mkdir -p /opt/mycookbook
sudo chown cookbook:cookbook /opt/mycookbook
```

Copy/clone the repository into `/opt/mycookbook` and run the Linux quick-start install/build commands there with write access as the `cookbook` account. For example `sudo -u cookbook -H /bin/bash` starts a shell for installation; do not run the application as root. Install Node through its official distribution or your OS's maintained package source. Set absolute runtime paths in `.env`:

```dotenv
COOKBOOK_DATABASE_URL=sqlite:////opt/mycookbook/instance/cookbook.db
COOKBOOK_DATA_DIR=/opt/mycookbook/instance
COOKBOOK_HOST=0.0.0.0
COOKBOOK_PORT=5432
```

Then install and start the supplied service:

```sh
sudo cp deploy/mycookbook.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mycookbook
sudo systemctl status mycookbook
journalctl -u mycookbook -f
```

Gunicorn defaults to one worker with two threads; increase `COOKBOOK_WORKERS` only when hardware and workload justify it. For production install `requirements-prod.txt`, which excludes pytest. The example service grants writes only to `instance/`; make sure it is owned by `cookbook`. Keep backups outside the source checkout on another disk/device. No Node process remains running after the build. CPU architecture-specific dependencies must be installed on the Pi; do not copy a Windows virtual environment or `node_modules` to it. The Pi 3 uses the separate service and layout documented in [DEPLOYMENT.md](DEPLOYMENT.md).

This is a single-household app without user accounts. Anyone who can reach it can read and edit its data. Keep it on a trusted LAN; do not forward its port to the public internet. For remote access, use an authenticated VPN or add a reverse proxy with HTTPS and authentication. Wake lock is browser-dependent and generally requires HTTPS (localhost is a development exception); cooking mode remains usable without it. Timers update to wall-clock time when the tab resumes but cannot guarantee alarms while a phone suspends the browser.

Browser requests that change API data must come from the same origin (scheme, hostname and port). Requests with foreign/null Origins, cross-site Fetch Metadata, or foreign Referers are rejected before any mutation or LLM call. Headerless CLI/API clients remain supported; these checks prevent browser cross-origin attacks and are not authentication. Framing is limited to the same origin. Access via `http://localhost:5432` or the server's LAN IP works automatically. For a hostname such as `cookbook.local`, add `COOKBOOK_ALLOWED_HOSTS=cookbook.local` and restart. This does not grant other origins permission to change data. Vite's proxy preserves the browser's Host header, so hot reload continues to work without allowing arbitrary origins. Reverse proxies must preserve the original Host and correctly convey the original scheme; forwarded headers are not blindly trusted by the app.

Image uploads use Pillow 13+ and restrict decoder selection to JPEG, PNG and WebP before parsing. Upload size and pixel limits still apply. After updating dependencies or application code, restart the server so the new decoder and request checks take effect.

## Database and demo data

Initialize or upgrade with `python -m flask --app wsgi db upgrade`. After model/schema changes, generate a migration with `python -m flask --app wsgi db migrate -m "Describe change"`, review it, and upgrade. Back up before upgrades. The app does not silently initialize production tables.

Use `python -m flask --app wsgi demo` to load six sample recipes and `python -m flask --app wsgi demo --remove` to remove only marked demos. The Settings page provides the same controls. Samples are demonstration content written for this application, not recovered historical ChatGPT recipes. Editing a demo keeps its demo marker; duplicating it creates a personal copy.

## Import, export and recipe quantities

Use **Import recipe** to upload/paste one recipe object, a JSON array or a versioned collection. Validation runs before saving; errors identify the offending field. Review duplicate title matches, compare fields, then choose skip, import separately or replace content. Multiple existing matches cannot be replaced ambiguously. Replacement always preserves the existing personal feedback and history. A new separate import starts with empty personal data unless restoration is explicitly selected.

For text import, use a title followed by optional `Servings: 2`, `Prep time: 10 minutes`, `Cook time: 20 minutes`, `Tags: Quick, Dinner`, `Equipment: Hob` lines, then `Ingredients` and `Instructions` (or `Method`) headings. Numeric decimals, fractions, mixed fractions and common Unicode fractions are supported. Missing quantities remain null. Review and correct the extraction in the recipe form; unstructured prose beyond these conventions may require manual adjustment or the optional LLM.

Portion selection uses `base quantity × selected servings / default servings`. Original quantities never change, and rounding applies only to display. Units, temperatures, timings and methods stay as written. Last selected portions are stored per recipe on the server. Shopping additions use the visible portion count; optional ingredients are excluded unless selected. Identical normalized ingredient names aggregate in compatible units (`kg→g`, `l→ml`), even when preparation notes differ. Distinct preparation notes are retained on the combined row; each recipe keeps its own instructions. Purchased items, teaspoons/grams and ambiguous quantities remain separate. Pantry matching is word-based with common aliases; suggestions are explainable rather than AI-generated.

See [JSON format](docs/json-format.md), the generated [JSON Schema](docs/recipe.schema.json) and [API reference](docs/api.md). Export a recipe from its detail page or the whole collection from Settings. JSON personal backups include feedback/history/settings/shopping; image paths refer to locally uploaded files, so use an archive for full recovery including photos.

### Cupboard staples

Recipe shopping additions automatically skip your **Always have** ingredients. Salt (including sea/table salt) and black pepper (including ground black pepper) are included by default. Open **Settings → Cupboard staples** to edit the list, or use **Add common sauces, oils & seasonings** to fill it with a starting selection and then save preferences. This is a shopping preference; it does not change recipe ingredients or recommendation exclusions.

On the shopping list, tap **Always have** beside an item to remember it and remove its current unchecked entries. Future recipe additions will skip that ingredient. Matching uses the complete normalized ingredient name, so black pepper does not exclude red peppers or pepper sauce. Add different names, such as light/dark soy sauce, separately. When a staple runs out, add it manually or tick **Include cupboard staples this time** on a recipe. Removing a staple from Settings includes it in future shopping additions. Staples are saved with settings and included in personal backups.

## Complete backup and restore

Run from the repository root, with the same environment as the server:

```sh
python -m scripts.backup /path/to/backups/mycookbook.zip
```

This uses SQLite's online backup API to take a consistent database snapshot, then includes uploads. It can run while the app is available, though stopping the service gives the strongest consistency between a database snapshot and simultaneous photo uploads. Keep backups private: they include personal notes and history. `.env` credentials are not included.

Restore into an installation of the same or newer app version:

```sh
sudo systemctl stop mycookbook
# Run as the cookbook service user with its environment:
python -m scripts.backup /path/to/backups/before-restore.zip
python -m scripts.restore /path/to/backups/mycookbook.zip --replace
python -m flask --app wsgi db upgrade
sudo systemctl start mycookbook
```

Restore validates archive paths and database integrity before replacing the database. It retains `cookbook.pre-restore.db` beside the database for recovery and refuses to overwrite an existing recovery copy. Move that copy to safe storage before another restore. Photos are copied by safe generated names, and existing unreferenced photos are retained. Do not restore while any server process is using the database. Use the full archive when moving machines; JSON merging intentionally preserves existing personal data on content replacement.

## Checks

```sh
python -m pytest -q
cd frontend
npm test
npm run build
```

Tests cover CRUD, filters/sorting, malformed imports, duplicate decisions, personal-data retention, fractional parsing, scaled shopping totals, incompatible units, feedback, history, settings, pantry matching, recommendations and uploaded image validation. Frontend tests exercise scaling, portion limits, clearing ratings and shopping requests with selected servings. The production build performs strict TypeScript checking. For smoke testing, use a temporary `COOKBOOK_DATA_DIR` and database, migrate, load demos and check `/api/health`, `/api/recipes` and `/` over HTTP.

## Troubleshooting

- **No such table:** run migrations against the same database URL/data directory used by the server.
- **Frontend not built:** run `npm ci` then `npm run build` in `frontend/`; Flask serves `frontend/dist`.
- **Cannot reach from phone:** use a LAN bind address, same network and appropriate firewall rules. `localhost` on a phone refers to the phone.
- **No suggestions:** check available equipment, ingredient/dietary exclusions, time filters and disliked status. Pantry matches do not require every ingredient.
- **Import rejected:** inspect the readable field errors and schema, then correct the data. Version 1 uses numeric decimal quantities; e.g. `0.5`, not `"1/2"` in JSON. Text import handles fraction notation.
- **LLM unavailable:** verify base URL, model and key; use local text parsing or JSON without any API.
- **Images missing after JSON import:** transfer a full archive backup or upload photos again.
- **Permission denied:** service user needs read access to source/build and write access to the configured data directory; check `journalctl`.

Project conventions for future development are in [AGENTS.md](AGENTS.md).
