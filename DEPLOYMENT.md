# Raspberry Pi 3 deployment

Target: SSH alias `recipe-pi`, account `leon`, hostname `rpi3`, LAN address `192.168.0.123`.
Inspected hardware: four Cortex-A53 cores at up to 1.2 GHz, aarch64/64-bit Debian 13.7, about 905 MiB RAM, Python 3.13.5, a 7.4 GiB SD card. Initial root free space was only about 6 MiB. The owner approved archiving and removing two inactive Codex executable bundles to reclaim about 659 MiB; bundle configuration and SSH files are excluded from that operation.

## Layout and resource settings

- Application root: `/home/leon/apps/mycookbook`
- Versioned source, built frontend and isolated production venv: `releases/<release-id>/`
- Active release symlink: `current` → `releases/20261123-100107-git` (Git commit `07b61f4`)
- Environment: `shared/.env` (mode 600; never print or commit)
- Persistent database and photos: `shared/data/cookbook.db`, `shared/data/uploads/`
- Pre-migration backups: `shared/backups/`
- Incoming packages: `incoming/`
- System service: `mycookbook.service`
- Expected URL: `http://192.168.0.123:5432` (port 5432 was unused during inspection)

Gunicorn uses one `gthread` worker, two threads, a 60-second timeout and periodic worker recycling. Its unused control socket is disabled. The systemd unit in `deploy/recipe-pi.service` runs as the existing non-root account, restarts on failures, starts at boot and restricts writes to `shared/`. MemoryHigh is configured as 256 MiB and MemoryMax as 384 MiB, but this Pi's kernel does not expose the memory cgroup controller, so these limits are currently **not enforced** and MemoryCurrent is unavailable. No kernel or boot configuration was changed. Observed combined master/worker RSS was about 96 MiB (includes shared pages). No Vite, Node runtime, development dependencies or extra reverse proxy are needed on the Pi. The service binds to the Pi's private LAN address, not a public interface. The desktop and all unrelated services are retained.

Python production dependencies are in `requirements-prod.txt`. `requirements.txt` includes those plus pytest for local development. Gunicorn is constrained to supported 26.x; Pillow remains patched 13.x. Installation uses prebuilt ARM64 wheels and disables pip caching to avoid expensive compilation and wasting SD storage. Updates require spare space for both old and new environments. Do not delete older releases or unrelated files automatically.

## Build and package locally

### Git-based releases (preferred from 23 November 2026)

Application source is cloned directly from `https://github.com/LeonPratt/MyCookBook.git` into a new versioned release. Do not copy local source files into that checkout or run `git pull` in the live release. Preserve `shared/.env`, `shared/data`, and existing releases for recovery. The Git checkout deliberately excludes built frontend assets, so build those on the laptop from the same commit and transfer only the generated `frontend/dist` artifact. No Node process runs on the Pi.

From the laptop, confirm the fix has been committed and pushed; record `git rev-parse HEAD`. Choose a unique release ID. On the Pi:

```sh
git clone --depth 1 https://github.com/LeonPratt/MyCookBook.git /home/leon/apps/mycookbook/releases/RELEASE
cd /home/leon/apps/mycookbook/releases/RELEASE
git rev-parse HEAD
python3 -m venv .venv
.venv/bin/python -m pip install --no-cache-dir --only-binary=:all: -r requirements-prod.txt
.venv/bin/python -m pip check
```

Compare the cloned commit with the tested laptop commit. Build using the local frontend test/build commands below. Package only `frontend/dist` as a tar archive containing `dist/`, transfer it into `incoming/`, verify SHA-256 and safely extract into the cloned `frontend/` directory. Never include `.env`, database files or dependency folders. If this repository is private, configure Git authentication separately without putting tokens in URLs, command history or logs.

Before switching, run the clone's `scripts.smoke` on temporary data, compare migrations with the current release, back up the live household data and retain a checksum-verified laptop copy. Use the approved service stop/symlink/start sequence in “Future updates and rollback.” No database migration is needed when migration files and the recorded schema revision are unchanged. The systemd unit continues to use `current`, so no unit reinstall is needed.

### Original archive workflow

From the repository root in PowerShell (substitute your Python environment if needed):

```powershell
Set-Location frontend
npm ci
npm test
npm run build
Set-Location ..
.\.venv-dev\Scripts\python.exe -m pytest -q
$release = Get-Date -Format 'yyyyMMdd-HHmmss'
.\.venv-dev\Scripts\python.exe -m scripts.package_release "backups/pi-deployment/mycookbook-$release.tar.gz"
```

The package allowlist includes application source, migration files, production configuration, scripts and `frontend/dist`. It excludes `.env`, databases, photos, Git metadata, virtual environments, tests and node_modules. The sidecar manifest records all files and the archive SHA-256. Transfer environment and initial data separately through SSH only. An installed system service does not rebuild the frontend.

## Initial deployment

Inspect `ssh recipe-pi`, available space, existing deployment paths, services and `ss -ltn` before changing anything. Do not reuse a pre-existing directory unless its purpose and ownership are confirmed. Initialize the new application root with mode 700 and a `.mycookbook-deployment` file containing `MyCookBook deployment v1`; create `releases`, `incoming`, `shared/data/uploads`, and `shared/backups` beneath it.

Use SCP to transfer the package to `incoming/`:

```powershell
scp "backups/pi-deployment/mycookbook-$release.tar.gz" recipe-pi:/home/leon/apps/mycookbook/incoming/
$digest = (Get-FileHash "backups/pi-deployment/mycookbook-$release.tar.gz" -Algorithm SHA256).Hash.ToLower()
Get-Content -Raw scripts/stage_pi_release.py | ssh recipe-pi "python3 - /home/leon/apps/mycookbook/incoming/mycookbook-$release.tar.gz --base /home/leon/apps/mycookbook --release $release --sha256 $digest"
```

Staging validates the checksum/archive paths, refuses an existing release, creates a new venv, installs only production wheels, and runs pip check. It does not change the active release, environment, database or system service.

Populate `shared/.env` privately. Use absolute paths and the inspected private IP:

```dotenv
COOKBOOK_DATABASE_URL=sqlite:////home/leon/apps/mycookbook/shared/data/cookbook.db
COOKBOOK_DATA_DIR=/home/leon/apps/mycookbook/shared/data
COOKBOOK_HOST=192.168.0.123
COOKBOOK_PORT=5432
COOKBOOK_WORKERS=1
COOKBOOK_THREADS=2
COOKBOOK_ALLOWED_HOSTS=rpi3,rpi3.local,recipe-pi
COOKBOOK_MAX_UPLOAD_MB=8
```

Preserve configured `LLM_API_URL`, `LLM_MODEL` and `LLM_API_KEY` privately if transferring the optional importer. No external API is needed to deploy or verify the app. Never echo the environment file or use shell tracing around credentials.

The local collection should be transferred using `python -m scripts.backup` (SQLite online snapshot plus photos), verified, and restored only into a verified empty destination. Never copy an actively written SQLite file directly. Keep the development copy unchanged. Before any migration of existing data, create a complete backup and retain it outside the Pi as well.

Run management commands with `shared/.env` loaded by the management helper. Do not source arbitrary env files as executable shell code. From a staged release on the Pi:

```sh
.venv/bin/python -m scripts.manage --env-file /home/leon/apps/mycookbook/shared/.env backup /home/leon/apps/mycookbook/shared/backups/pre-migration-RELEASE.zip
.venv/bin/python -m scripts.manage --env-file /home/leon/apps/mycookbook/shared/.env migrate
.venv/bin/python -m scripts.manage --env-file /home/leon/apps/mycookbook/shared/.env check
.venv/bin/python -m scripts.smoke
```

The smoke script uses temporary data and production dependencies only; it never changes the household collection. Once migration and smoke tests succeed, create `current` pointing to that release. Review and validate `deploy/recipe-pi.service` with `systemd-analyze verify` before requesting approval to install/enable it.

**Administrator approval is required** before sudo, system package changes, systemd installation/restarts, firewall changes or destructive operations. The new service installation uses only:

```sh
sudo install -m 0644 /home/leon/apps/mycookbook/current/deploy/recipe-pi.service /etc/systemd/system/mycookbook.service
sudo systemctl daemon-reload
sudo systemctl enable --now mycookbook.service
```

Do not overwrite an existing unit without first inspecting and backing it up. No firewall or router changes are expected. Do not add port forwarding, public tunnels or weaken SSH settings.

## Verification and logs

```sh
systemctl status mycookbook.service --no-pager
systemctl is-enabled mycookbook.service
journalctl -u mycookbook.service -n 100 --no-pager
journalctl -u mycookbook.service -f
curl --fail http://192.168.0.123:5432/api/health
curl --fail http://192.168.0.123:5432/
```

Check built asset URLs from the returned HTML. Test JSON import, serving selection, shopping aggregation and persistence first on an isolated temporary database. Do not test deletion/import on the personal collection. Compare database recipe counts/history/settings/photo counts before and after transfer and service restart. The frontend portion formula is covered by local interaction tests; verify on a phone by changing portions and checking that original quantities remain unchanged.

After approval, test `sudo systemctl restart mycookbook.service` and poll the health endpoint until it succeeds. Verify `NRestarts`, memory usage, active unit configuration and that no Vite process is running. Boot persistence follows from the enabled system unit; a physical reboot should be tested only with explicit approval because it interrupts unrelated services.

## Future updates and rollback

1. Build/test/package locally with a new release ID; transfer and stage as above. Never replace `shared/.env` or `shared/data` with package contents.
2. Check free storage, service status and existing migrations. Download a current archive backup from the Pi to the laptop. Obtain approval before service changes or any potentially destructive migration.
3. Stop only `mycookbook.service` for migrations, take a complete backup using the active release and shared environment, then run migrations using the new release. If migrations fail, keep the service stopped until a verified recovery is chosen; do not overwrite the database blindly.
4. Atomically replace the `current` symlink with one pointing to the new release (first confirm the old link points inside this deployment). Restart only MyCookBook, then repeat API/static/persistence checks.
5. Keep the previous release and pre-migration database/photo backup. Code rollback is safe only if the old code supports the new schema. Otherwise stop the service and restore the complete matching backup before switching back; follow `scripts.restore --replace` safeguards and obtain approval.

Retire old releases only after verifying their targets, preserving the active and previous releases, and obtaining deletion approval. This Pi has very limited SD space. For substantial recipe photos or several retained environments, use a larger SD card or dedicated storage rather than deleting unrelated programs.

After staging, an approved update can use these commands on the Pi (replace `RELEASE` and `BACKUP` with unique values). Inspect the resolved current/new paths before changing the symlink. Run the isolated smoke check before stopping the service:

```sh
cd /home/leon/apps/mycookbook/releases/RELEASE
.venv/bin/python -m scripts.smoke
sudo systemctl stop mycookbook.service
/home/leon/apps/mycookbook/current/.venv/bin/python -m scripts.manage --env-file /home/leon/apps/mycookbook/shared/.env backup /home/leon/apps/mycookbook/shared/backups/BACKUP.zip
```

Download and checksum the backup from the laptop before migrating:

```powershell
scp recipe-pi:/home/leon/apps/mycookbook/shared/backups/BACKUP.zip backups/pi-deployment/
Get-FileHash backups/pi-deployment/BACKUP.zip -Algorithm SHA256
ssh recipe-pi "sha256sum /home/leon/apps/mycookbook/shared/backups/BACKUP.zip"
```

Compare both checksums, then continue in the new release directory on the Pi:

```sh
.venv/bin/python -m scripts.manage --env-file /home/leon/apps/mycookbook/shared/.env migrate
.venv/bin/python -m scripts.manage --env-file /home/leon/apps/mycookbook/shared/.env check
```

Stop if any command fails. When checks pass, switch the symlink atomically from the deployment root (the temporary name must not already exist), then restart and verify:

```sh
cd /home/leon/apps/mycookbook
ln -s /home/leon/apps/mycookbook/releases/RELEASE current.next
mv -T current.next current
sudo systemctl start mycookbook.service
systemctl is-active mycookbook.service
curl --fail http://192.168.0.123:5432/api/health
```

Changing Python app code or its Gunicorn configuration does not require reinstalling the systemd unit. Changes to the unit itself require review, approval, installation and `sudo systemctl daemon-reload`.

## Deployment verification record

### Git update: 23 November 2026

- Active release: `/home/leon/apps/mycookbook/releases/20261123-100107-git`, cloned directly from `https://github.com/LeonPratt/MyCookBook.git`, commit `07b61f405e5bf47efc473feaed082f8460d263cf` (`bugfix`). Application source was not copied manually. Only generated frontend assets were transferred from the matching local build.
- The clone has its own production venv and an unmodified Git working tree. No migration, system package installation, systemd unit change or environment replacement was required.
- With owner approval, stopped only MyCookBook, created `shared/backups/cutover-20261123-100107-git.zip`, atomically switched `current` and started the service. The database was exactly unchanged across cutover. The previous release `20261122-114957` remains intact for rollback.
- Pi smoke tests and the specific checked-ingredient exclusion regression passed using temporary databases. Live health, recipe listing and generated JS/CSS checks passed; the service is active and enabled at boot. The new JS includes the ingredient-exclusion request field.
- A checksum-verified laptop copy of the cutover backup is under `backups/pi-deployment/`; an earlier pre-update backup was also restored into temporary storage and passed SQLite integrity checks with all 21 recipes.

### Initial deployment: 22 November 2026

- Initially deployed on 22 November 2026: release `20261122-114957`, under `/home/leon/apps/mycookbook/releases/20261122-114957`; retained as the previous release after the Git update.
- `mycookbook.service` installed with owner approval, active and enabled for boot; restart-on-failure configured. A service restart changed the Gunicorn master PID, recovered healthy responses and left the database exactly unchanged. No full Pi reboot was performed.
- A second approved restart applied the disabled optional Gunicorn control socket; startup logs were clean and the database again remained unchanged. The deployed Gunicorn configuration includes that fix in addition to the original release archive.
- Laptop-to-Pi HTTP checks passed for `/api/health`, `/api/recipes`, `/` and both generated JS/CSS assets. Port 5432 listens only on `192.168.0.123`; existing SSH/rpcbind listeners were preserved.
- Production environment: Python 3.13.5, Gunicorn 26.2.0, Pillow 13.0.0; binary ARM64 wheels only, `pip check` passed, no system package installation needed.
- Local validation: 85 backend tests, 9 frontend tests and strict TypeScript/production build passed. Pi smoke checks passed with temporary data for migrations, JSON import/export and duplicate handling, selected portions/scaled shopping without changing base quantities or timers, history, photo uploads, origin rejection, static assets and fresh-app persistence.
- Transferred 21 recipes, settings, history/shopping state and photos using a verified SQLite snapshot. Personal settings changed through the live app after deployment were preserved. No verification imports or deletions were performed on the household database.
- Pi pre-migration backup: `shared/backups/pre-migration-20261122-114957.zip`; checksum-verified laptop copy: `backups/pi-deployment/pre-migration-20261122-114957.zip`. A restore of that downloaded backup into a temporary directory passed SQLite integrity and recipe-count checks.
- About 578 MiB remained free after installation. Master/worker RSS was about 96 MiB; memory cgroup limits are unavailable on this kernel as explained above.
- The approved Codex bundle archive is retained on the laptop at `backups/pi-deployment/codex-bundles-20261122-114543.tar.gz`, with manifest and verification record beside it. All 93 archive entries were verified before removing only the two approved remote executable directories. Restoring those bundles requires sufficient additional Pi storage; configuration and SSH files were untouched.
- No public exposure, router/firewall changes, SSH changes, unrelated service changes or mandatory external API calls were introduced.
