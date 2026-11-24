import asyncio
import copy
import logging
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

pytest.importorskip("mcp")

from sqlalchemy.exc import OperationalError

from cookbook.models import Recipe, db
from cookbook.schemas import RecipeInput


def call(server, name, **arguments):
    response = asyncio.run(server.call_tool(name, arguments))
    assert response.isError is (not response.structuredContent["success"])
    return response.structuredContent


def test_create_shares_web_database_and_schema(server, app, recipe, caplog):
    with caplog.at_level(logging.INFO, logger="mycookbook.mcp.audit"):
        saved = call(server, "add_recipe", recipe=recipe)
    assert saved["success"] and saved["title"] == recipe["title"]
    assert saved["url"] == f"http://localhost:5432/#recipe/{saved['recipe_id']}"
    row = app.test_client().get(f"/api/recipes/{saved['recipe_id']}").json
    assert row["ingredients"][0]["group"] == "Main"
    assert row["ingredients"][1]["quantity"] == 0.5
    assert row["ingredients"][2]["quantity"] is None
    assert row["instructions"][0]["timer_seconds"] == 180
    assert row["equipment_alternatives"] == recipe["equipment_alternatives"]
    assert "operation=add_recipe status=success" in caplog.text
    assert "Family notes" not in caplog.text
    schema = call(server, "get_recipe_schema")
    assert schema["recipe_schema"] == RecipeInput.model_json_schema()
    assert schema["schema_version"] == 1
    assert call(server, "get_recipe", recipe_id=saved["recipe_id"])["recipe"] == row


@pytest.mark.parametrize("change", [
    {"unknown": 1}, {"servings": 0}, {"servings": float("inf")},
    {"ingredients": [{"name": "rice", "quantity": -1}]},
    {"ingredients": [{"name": "rice", "quantity": float("nan")}]},
    {"ingredients": [{"name": "rice", "quantity": float("inf")}]},
    {"ingredients": [{"name": "rice", "quantity": 1, "unexpected": "x"}]},
    {"image_path": "../../private.jpg"}, {"image_path": "https://external.invalid/pic.jpg"},
    {"instructions": [{"text": "Cook", "timer_seconds": 0}]}, {"ingredients": []},
])
def test_invalid_recipe_is_structured_and_writes_nothing(server, app, recipe, change):
    data = call(server, "add_recipe", recipe={**recipe, **change})
    assert data["error"]["code"] == "validation_error"
    assert data["error"]["details"]
    assert app.test_client().get("/api/recipes").json == []


def test_duplicate_single_and_bulk_are_atomic(server, app, recipe):
    first = call(server, "add_recipe", recipe=recipe)
    duplicate = call(server, "add_recipe", recipe={**recipe, "title": "  LEMON CHICKEN  "})
    assert duplicate["error"]["code"] == "duplicate_recipe"
    assert duplicate["error"]["details"]["recipe_id"] == first["recipe_id"]
    batch = call(server, "add_recipes", recipes=[{**recipe, "title": "New meal"}, recipe])
    assert batch["error"]["code"] == "duplicate_recipe"
    assert len(app.test_client().get("/api/recipes").json) == 1
    repeated = call(server, "add_recipes", recipes=[{**recipe, "title": "New meal"}] * 2)
    assert repeated["error"]["code"] == "duplicate_recipe"
    assert len(app.test_client().get("/api/recipes").json) == 1


def test_bulk_valid_invalid_and_limits(server, app, recipe):
    bad = copy.deepcopy(recipe)
    bad["ingredients"][0]["quantity"] = -1
    assert not call(server, "add_recipes", recipes=[recipe, bad])["success"]
    assert app.test_client().get("/api/recipes").json == []
    assert not call(server, "add_recipes", recipes=[])["success"]
    assert not call(server, "add_recipes", recipes=[recipe] * 101)["success"]
    data = call(server, "add_recipes", recipes=[recipe, {**recipe, "title": "Another meal"}])
    assert data["imported"] == 2
    assert [r["title"] for r in data["recipes"]] == ["Lemon chicken", "Another meal"]
    assert len(app.test_client().get("/api/recipes").json) == 2


@pytest.mark.parametrize("filters", [
    {"query": "lemon"}, {"query": "chicken breast"}, {"query": "Italian"},
    {"query": "Dinner"}, {"query": "Weeknight"}, {"ingredient": "chicken"},
    {"cuisine": "Italian", "category": "Dinner"},
])
def test_search(server, recipe, filters):
    saved = call(server, "add_recipe", recipe=recipe)
    data = call(server, "search_recipes", **filters)
    assert data["total"] == 1 and data["recipes"][0]["recipe_id"] == saved["recipe_id"]
    assert call(server, "search_recipes", query="nonexistent")["total"] == 0


def test_pagination(server, recipe):
    call(server, "add_recipes", recipes=[{**recipe, "title": t} for t in ["C", "A", "B"]])
    first = call(server, "list_recipes", limit=2)
    assert [r["title"] for r in first["recipes"]] == ["A", "B"]
    assert first["total"] == 3 and first["next_offset"] == 2
    last = call(server, "list_recipes", limit=2, offset=first["next_offset"])
    assert [r["title"] for r in last["recipes"]] == ["C"]
    assert last["next_offset"] is None
    assert call(server, "list_recipes", offset=10)["recipes"] == []
    for args in [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": True}]:
        assert not call(server, "list_recipes", **args)["success"]


def test_update_preserves_personal_history_scaling_and_metadata(server, app, recipe):
    client = app.test_client()
    saved = client.post("/api/recipes", json=recipe).json
    recipe_id = saved["id"]
    personal = {"favourite": True, "feedback": "negative", "rating": 4, "notes": "Keep", "would_cook_again": False, "selected_servings": 3}
    client.patch(f"/api/recipes/{recipe_id}/personal", json=personal)
    client.post(f"/api/recipes/{recipe_id}/history", json={"servings": 3, "rating": 5})
    full = call(server, "get_recipe", recipe_id=recipe_id)["recipe"]
    content = {k: v for k, v in full.items() if k in RecipeInput.model_fields}
    updated = call(server, "update_recipe", recipe_id=recipe_id, recipe={**content, "title": "Updated chicken"}, expected_updated_at=full["updated_at"])
    assert updated["success"]
    row = client.get(f"/api/recipes/{recipe_id}").json
    assert row["personal"] == personal and row["history"] == full["history"]
    assert row["ingredients"] == full["ingredients"] and row["instructions"] == full["instructions"]
    conflict = call(server, "update_recipe", recipe_id=recipe_id, recipe=content, expected_updated_at=full["updated_at"])
    assert conflict["error"]["code"] == "conflict"
    assert call(server, "update_recipe", recipe_id=recipe_id, recipe={**content, "title": "Updated chicken"})["updated_at"] == updated["updated_at"]
    shopping = client.post(f"/api/recipes/{recipe_id}/shopping", json={"servings": 3}).json
    assert next(i for i in shopping if i["name"] == "chicken breast")["quantity"] == 450


def test_missing_invalid_and_duplicate_update(server, recipe):
    assert call(server, "get_recipe", recipe_id=999)["error"]["code"] == "not_found"
    assert call(server, "get_recipe", recipe_id=0)["error"]["code"] == "validation_error"
    assert call(server, "update_recipe", recipe_id=999, recipe=recipe)["error"]["code"] == "not_found"
    saved = call(server, "add_recipe", recipe=recipe)
    call(server, "add_recipe", recipe={**recipe, "title": "Other"})
    assert call(server, "update_recipe", recipe_id=saved["recipe_id"], recipe={**recipe, "title": "Other"})["error"]["code"] == "duplicate_recipe"


def test_database_commit_error_rolls_back_entire_batch(server, app, recipe, caplog):
    with app.app_context():
        session = db.session()
        # Scoped sessions are specific to the adapter's context, so patch the class.
        with patch.object(type(session), "commit", side_effect=OperationalError("SECRET_SQL", {}, Exception("SECRET_CREDENTIAL"))):
            data = call(server, "add_recipes", recipes=[recipe, {**recipe, "title": "Other"}])
    assert data["error"]["code"] == "database_error"
    assert "SECRET" not in str(data) + caplog.text
    assert app.test_client().get("/api/recipes").json == []
    assert call(server, "add_recipe", recipe=recipe)["success"]


def test_concurrent_duplicate_prevention(app, config, recipe):
    from mcp_server.server import create_server
    def add(_):
        return call(create_server(config, app), "add_recipe", recipe=recipe)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(add, range(2)))
    assert sum(r["success"] for r in responses) == 1
    with app.app_context():
        assert db.session.query(Recipe).count() == 1


def test_schema_annotations_and_no_delete(server):
    tools = {t.name: t for t in asyncio.run(server.list_tools())}
    assert set(tools) == {"add_recipe", "add_recipes", "get_recipe", "search_recipes", "list_recipes", "update_recipe", "get_recipe_schema"}
    assert tools["get_recipe"].annotations.readOnlyHint
    assert tools["update_recipe"].annotations.destructiveHint
    assert tools["update_recipe"].annotations.idempotentHint
    assert not tools["add_recipe"].annotations.readOnlyHint
    recipe_schema = tools["add_recipe"].inputSchema["$defs"]["RecipeInput"]
    assert recipe_schema["additionalProperties"] is False
    assert tools["add_recipe"].inputSchema["additionalProperties"] is False
    assert call(server, "list_recipes", unexpected="ignored?")["error"]["code"] == "validation_error"
