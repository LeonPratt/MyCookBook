"""Thin adapter to cookbook persistence, imports and search; no second database."""

import logging
from collections.abc import Callable

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from cookbook.models import Recipe, db, now
from cookbook.routes import filtered_recipes
from cookbook.schemas import RecipeInput
from cookbook.services import SCHEMA_VERSION, import_records, serialize, title_key, transfer_records

audit = logging.getLogger("mycookbook.mcp.audit")


class OperationError(Exception):
    def __init__(self, code, message, details=None):
        self.code, self.message, self.details = code, message, details


def validation_details(error):
    # Do not return Pydantic's raw input or exception context.
    return [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in error.errors()]


class CookbookService:
    def __init__(self, app, recipe_base_url=""):
        self.app = app
        self.recipe_base_url = recipe_base_url.rstrip("/")

    def summary(self, recipe):
        return {
            "recipe_id": recipe.id, "title": recipe.content["title"],
            "url": f"{self.recipe_base_url}/#recipe/{recipe.id}" if self.recipe_base_url else None,
        }

    def execute(self, operation: str, action: Callable, *, write=False):
        with self.app.app_context():
            try:
                if write and db.engine.dialect.name == "sqlite":
                    # Serialize duplicate checks and writes across MCP processes.
                    # Also prevents a stale MCP read overwriting a concurrent web update.
                    db.session.execute(text("BEGIN IMMEDIATE"))
                data = action()
                if write:
                    db.session.commit()
                    audit.info("operation=%s status=success recipe_ids=%s", operation,
                               [r["recipe_id"] for r in data.get("recipes", [data])])
                return {"success": True, **data}
            except ValidationError as error:
                db.session.rollback()
                result = {"code": "validation_error", "message": "Correct the indicated recipe fields and retry.",
                          "details": validation_details(error)}
            except OperationError as error:
                db.session.rollback()
                result = {"code": error.code, "message": error.message}
                if error.details is not None:
                    result["details"] = error.details
            except SQLAlchemyError:
                db.session.rollback()
                result = {"code": "database_error", "message": "Database operation failed; nothing was saved. Check service health before retrying."}
            except Exception:
                db.session.rollback()
                # Deliberately exclude SQL, connection URLs, payloads and exception text.
                result = {"code": "internal_error", "message": "Operation failed; nothing was saved. Check service health."}
            if write:
                audit.warning("operation=%s status=failed code=%s", operation, result["code"])
            return {"success": False, "error": result}

    def add(self, recipes, *, single=False):
        def action():
            records = transfer_records([r.model_dump() for r in recipes])
            seen = set()
            existing = {title_key(r.content["title"]): r.id for r in db.session.scalars(db.select(Recipe))}
            for index, record in enumerate(records):
                key = title_key(record["content"]["title"])
                if key in seen or key in existing:
                    raise OperationError("duplicate_recipe", "A recipe title already exists or is repeated in this batch. Retrieve it to update, or choose a distinct title.",
                                         {"index": index, "recipe_id": existing.get(key)})
                seen.add(key)
            # Existing importer validates the entire collection before it writes.
            import_records(records, {})
            keys = {title_key(r["content"]["title"]) for r in records}
            saved = {title_key(r.content["title"]): r for r in db.session.scalars(db.select(Recipe))
                     if title_key(r.content["title"]) in keys}
            summaries = [self.summary(saved[title_key(r["content"]["title"])]) for r in records]
            return summaries[0] if single else {"recipes": summaries, "imported": len(summaries)}
        return self.execute("add_recipe" if single else "add_recipes", action, write=True)

    def get(self, recipe_id):
        def action():
            recipe = db.session.get(Recipe, recipe_id)
            if recipe is None:
                raise OperationError("not_found", "Recipe not found. Search or list recipes to obtain a valid ID.")
            return {"recipe": serialize(recipe), **self.summary(recipe)}
        return self.execute("get_recipe", action)

    def list(self, limit, offset, filters=None):
        def action():
            # Reuse the same search/filter semantics as the existing Flask API.
            recipes = filtered_recipes({"sort": "alphabetical", **(filters or {})})
            # Stable tie breaking for deterministic pagination.
            recipes.sort(key=lambda r: (r.content["title"].casefold(), r.id))
            page = recipes[offset:offset + limit]
            return {"recipes": [{"recipe": serialize(r, False), **self.summary(r)} for r in page],
                    "total": len(recipes), "limit": limit, "offset": offset,
                    "next_offset": offset + limit if offset + limit < len(recipes) else None}
        return self.execute("search_recipes" if filters is not None else "list_recipes", action)

    def update(self, recipe_id, recipe, expected_updated_at=None):
        def action():
            current = db.session.get(Recipe, recipe_id)
            if current is None:
                raise OperationError("not_found", "Recipe not found. Search or list recipes to obtain a valid ID.")
            if expected_updated_at is not None and current.updated_at != expected_updated_at:
                raise OperationError("conflict", "Recipe changed since retrieval. Get it again and review your update.")
            content = RecipeInput.model_validate(recipe.model_dump()).model_dump()
            if any(r.id != recipe_id and title_key(r.content["title"]) == title_key(content["title"])
                   for r in db.session.scalars(db.select(Recipe))):
                raise OperationError("duplicate_recipe", "Another recipe already uses that title. Choose a distinct title.")
            if current.content != content:
                current.content = content  # JSON reassignment is required by SQLAlchemy.
                current.updated_at = now()
            # Personal feedback, selected portions and cooking history remain intact.
            return {**self.summary(current), "updated_at": current.updated_at}
        return self.execute("update_recipe", action, write=True)

    @staticmethod
    def schema():
        return {"success": True, "schema_version": SCHEMA_VERSION,
                "recipe_schema": RecipeInput.model_json_schema(),
                "notes": "Quantities are original numeric amounts, or null when unspecified. Never scale timers, times or methods. Personal feedback/history are managed separately."}
