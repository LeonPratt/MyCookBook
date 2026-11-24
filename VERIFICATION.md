# Verification record

Verified on Windows with Python 3.12.13 and Node.js 26.12.0.

- Backend: `python -m pytest -q` — 80 tests pass, including migrated database initialization, restart/restore persistence, shopping aggregation, cupboard staples, Host/Origin/Fetch Metadata validation, blocked foreign uploads/LLM requests, rejected unsupported decoders and valid JPEG/PNG/WebP uploads.
- Frontend: `npm test` — 9 tests pass in three files. Includes portion scaling and limits, clearable star ratings, selected portions in shopping requests, structured recipe creation, duplicate replacement review, cooking-step completion with meal logging, remembering cupboard staples and the restocking checkbox.
- Production: `npm run build` — strict TypeScript checking and Vite build pass. Assets are served directly by Flask.
- Runtime: Waitress on loopback returns HTTP 200 for the built HTML, `/api/health` returns `status: ok`, and `/api/recipes` returns the six bundled demos.
- Dependency audits: `npm audit` reported zero known vulnerabilities. The security audit initially found 42 advisory entries in Pillow 12.3.0. Pillow was upgraded to 13.0.0 and constrained to patched 13.x releases; `pip-audit --path .venv-dev/Lib/site-packages` then reported no known vulnerabilities. Other Python environments and Raspberry Pi dependencies were not scanned.
- Recovery experiments caught and fixed Windows-held SQLite handles. Tests verify original quantities, personal notes, ratings, history, settings, checked shopping state and uploaded files survive restore; unsafe archive paths are rejected.
- Import validation checks caught and fixed malformed history values returning server errors. JSON restoration now keeps checked and unchecked quantities separate.
- Security HTTP smoke used a temporary in-memory database: same-origin health/create requests succeeded, foreign writes returned 403, untrusted Hosts returned 400, and the recipe count remained unchanged by rejected requests. Headerless CLI clients and normal private LAN origins remain supported. No authentication or new LLM rate limits were added; the user's OpenRouter key limits remain their chosen spending control.

The autonomous-build planner, coder, tester, experimenter and reviewer sessions were invoked, but those sessions had no filesystem/execution tools. Source implementation and the reported checks were performed in the primary session. Independent tester/experimenter evidence is unavailable; reviewer verdict is **INCONCLUSIVE**, not PASS. No independent review cycle completed.

Browser access was attempted through the supported computer-use tools. Browser integration was unavailable, and native Chrome selection was stopped because the tool could not establish the current URL safely. No visual browser/phone verification is claimed. Responsive CSS and the cooking interactions have automated coverage, but actual layout, wake lock and device behavior remain to be verified in a browser. No Raspberry Pi hardware deployment or configured LLM endpoint was available for testing.

The optional LLM remains disabled without configuration. No external service is required for the tested workflows. No Git commit or public deployment was made.
