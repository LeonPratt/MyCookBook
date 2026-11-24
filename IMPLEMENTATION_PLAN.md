# Implementation plan

Authoritative requirements: `codex.md`.

1. Build a Flask application factory, SQLAlchemy persistence, Alembic migrations and validated API contracts. Recipes hold ordered structured ingredients and steps; history, settings and shopping items persist separately.
2. Implement recipe CRUD, feedback, image uploads, search/filter/sort, history, recommendations, pantry matching, deterministic text parsing and optional OpenAI-compatible extraction.
3. Implement transactional versioned import/export with duplicate previews and personal-data preservation, compatible-unit shopping aggregation and complete backups.
4. Build a responsive React/TypeScript application with local assets, light/dark themes, recipe forms, portion scaling, cooking mode and all primary sections.
5. Add backend and frontend behavioral tests, demo data, deployment scripts, API/schema documentation and agent conventions.
6. Run tests, type checking, production build and HTTP smoke checks; inspect changes and document remaining verification limits.

Acceptance: the features in codex.md work through UI and API, persist across restarts, and run without an external service. Scaling leaves base quantities intact. Imports validate atomically. Replacing content retains personal feedback/history. Production serves built frontend through Flask without a Node process. Raspberry Pi instructions include migrations and recoverable backups.
