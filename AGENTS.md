# MyCookBook development

Read `codex.md` for requirements and `IMPLEMENTATION_PLAN.md` for milestones. Do not replace the user's specification. This is an offline-first, single-household application for a trusted LAN.

- Python: Flask application factory in `cookbook/__init__.py`, API routes in `routes.py`, schemas in `schemas.py`, persistence in `models.py`, pure matching/scaling/import services in `services.py`.
- Use Pydantic on all input boundaries. Reject unknown recipe fields, non-finite quantities and invalid servings. Return useful 4xx errors. Do not leak credentials or server errors.
- SQLAlchemy JSON columns must be reassigned when updated. Use migrations for schema changes; never run `create_all` as production initialization.
- Store original quantities only. Frontend scaling is quantity × selected/default; round for display only. Persist selected portions separately. Never scale cooking times, temperatures or methods.
- Favourite, like/dislike, rating, notes and would-cook-again are separate. Replacing imported content retains personal feedback and history.
- Keep imports transactional. Preview before applying. Version exported JSON and preserve backwards compatibility or document migration.
- Combine shopping quantities by normalized ingredient name and compatible units. Preparation notes (sliced/diced/etc.) do not split purchasing totals; retain distinct notes on the combined row and leave recipe instructions unchanged. Checked items, null quantities and incompatible units remain separate.
- Cupboard staples (`shopping_staples` in settings) are shopping exclusions, separate from recommendation exclusions. Use full normalized names, not fuzzy/substring matching. Recipe additions skip staples unless explicitly overridden; manual restocking remains available. Remembering a staple removes only matching unchecked shopping entries and preserves other settings.
- React uses TypeScript, local system fonts, Lucide and CSS/Tailwind. No external assets or cloud API may be mandatory. Keep phone cooking flows readable and accessible, including focus states and reduced motion.
- Never commit `.env`, databases, uploads, `.venv*`, dependency folders or built frontend artifacts. Preserve unrelated user changes.
- Backend: `python -m pytest -q`. Frontend: `cd frontend; npm test; npm run build` (PowerShell) or equivalent shell commands. Build includes strict TypeScript checking.
- Run migrations and smoke checks on a temporary database for deployment changes. Test backup/restore on temporary copies, never overwrite personal data during verification.
- Optional LLM extraction sends text only when explicitly selected; keys stay server-side. No other feature depends on it.
- Keep the Host/Origin/Fetch Metadata guards in `cookbook/security.py` before all API writes, including bodyless endpoints and uploads. Vite must preserve the incoming Host header. Extra hostnames are configured explicitly; do not allow arbitrary origins or trust forwarded headers without a proxy trust configuration.
- Keep Pillow on a patched release and pass the supported format allowlist to `Image.open` itself; checking image.format after unrestricted auto-detection permits unsupported parsers to run.
