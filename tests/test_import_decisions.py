import pytest


def test_exact_names_detect_duplicates_without_ingredient_aliases(client, recipe):
    client.post("/api/recipes", json={**recipe, "title": "Eggs"})
    data = [{**recipe, "title": title} for title in [" eggs ", "Egg", "Eggs!"]]
    preview = client.post("/api/import/preview", json={"data": data}).json
    assert [len(row["duplicates"]) for row in preview] == [1, 0, 0]


@pytest.mark.parametrize("name", [None, "Lemon chicken", " lemon CHICKEN ", "", " ", "x" * 201, 12])
def test_keep_both_requires_valid_different_name_and_is_atomic(client, recipe, name):
    client.post("/api/recipes", json=recipe)
    payload = {
        "data": [{**recipe, "title": "New dish"}, recipe],
        "actions": {"1": "separate"},
    }
    if name is not None:
        payload["renames"] = {"1": name}
    response = client.post("/api/import", json=payload)
    assert response.status_code == 422
    assert [r["title"] for r in client.get("/api/recipes").json] == [recipe["title"]]


def test_keep_both_renames_only_incoming_recipe(client, recipe):
    original = client.post("/api/recipes", json=recipe).json
    response = client.post("/api/import", json={
        "data": recipe, "actions": {"0": "separate"},
        "renames": {"0": "My lemon chicken"},
    })
    assert response.status_code == 200
    assert response.json["imported"] == 1
    assert {r["title"] for r in client.get("/api/recipes").json} == {
        "My lemon chicken", recipe["title"],
    }
    assert client.get(f"/api/recipes/{original['id']}").json == original


def test_batch_duplicates_are_previewed_and_must_be_renamed(client, recipe):
    data = [recipe, recipe]
    preview = client.post("/api/import/preview", json={"data": data}).json
    assert preview[0]["duplicate_indices"] == []
    assert preview[1]["duplicate_indices"] == [0]
    assert client.post("/api/import", json={
        "data": data, "actions": {"1": "separate"},
    }).status_code == 422
    assert client.get("/api/recipes").json == []
    result = client.post("/api/import", json={
        "data": data, "actions": {"1": "separate"},
        "renames": {"1": "Another lemon chicken"},
    })
    assert result.json["imported"] == 2


def test_rename_cannot_collide_with_existing_or_incoming_names(client, recipe):
    client.post("/api/recipes", json=recipe)
    client.post("/api/recipes", json={**recipe, "title": "Existing dish"})
    for renamed in ["EXISTING DISH", "New dish"]:
        response = client.post("/api/import", json={
            "data": [recipe, {**recipe, "title": "New dish"}],
            "actions": {"0": "separate"}, "renames": {"0": renamed},
        })
        assert response.status_code == 422
        assert len(client.get("/api/recipes").json) == 2
