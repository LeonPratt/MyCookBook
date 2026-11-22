import pytest


def create(client, recipe, ingredients):
    response = client.post("/api/recipes", json={**recipe, "ingredients": ingredients})
    assert response.status_code == 201
    return response.json["id"]


def test_default_staples_skip_salt_and_black_pepper_but_not_fresh_peppers(
    client, recipe
):
    ingredients = [
        {"name": name, "quantity": 1, "unit": "g"}
        for name in ["Salt", "ground black pepper", "red pepper", "pepper sauce"]
    ]
    recipe_id = create(client, recipe, ingredients)
    response = client.post(f"/api/recipes/{recipe_id}/shopping", json={"servings": 3})
    assert response.status_code == 201
    assert {i["name"] for i in response.json} == {"red pepper", "pepper sauce"}
    assert all(i["quantity"] == 1.5 for i in response.json)
    assert len(client.get(f"/api/recipes/{recipe_id}").json["ingredients"]) == 4


def test_custom_staples_persist_and_can_be_overridden_for_restocking(client, recipe):
    client.put(
        "/api/settings",
        json={
            "shopping_staples": [" light soy sauce ", "LIGHT SOY SAUCE", "", "paprika"]
        },
    )
    assert client.get("/api/settings").json["shopping_staples"] == [
        "light soy sauce",
        "paprika",
    ]
    recipe_id = create(
        client,
        recipe,
        [
            {"name": "LIGHT SOY SAUCE", "quantity": 20, "unit": "ml"},
            {"name": "chicken", "quantity": 300, "unit": "g"},
        ],
    )
    response = client.post(f"/api/recipes/{recipe_id}/shopping", json={})
    assert [i["name"] for i in response.json] == ["chicken"]
    response = client.post(
        f"/api/recipes/{recipe_id}/shopping", json={"include_staples": True}
    )
    assert {i["name"] for i in response.json} == {"LIGHT SOY SAUCE", "chicken"}
    assert next(i["quantity"] for i in response.json if i["name"] == "chicken") == 600


def test_remembering_staple_removes_unchecked_requirements_and_preserves_preferences(
    client, recipe
):
    client.put(
        "/api/settings",
        json={
            "theme": "dark",
            "default_servings": 4,
            "ingredient_exclusions": ["mushroom"],
        },
    )
    for item in [
        {"name": "soy sauce", "quantity": 10, "unit": "ml"},
        {"name": "soy sauce", "quantity": 1, "unit": "tbsp"},
        {"name": "soy sauce", "quantity": 5, "unit": "ml", "checked": True},
        {"name": "dark soy sauce", "quantity": 10, "unit": "ml"},
    ]:
        client.post("/api/shopping", json=item)
    rows = client.get("/api/shopping").json
    item_id = next(
        i["id"] for i in rows if i["name"] == "soy sauce" and not i["checked"]
    )
    response = client.post(f"/api/shopping/{item_id}/staple")
    assert response.status_code == 200
    assert len(response.json) == 2
    assert any(i["name"] == "soy sauce" and i["checked"] for i in response.json)
    assert any(i["name"] == "dark soy sauce" for i in response.json)
    settings = client.get("/api/settings").json
    assert "soy sauce" in settings["shopping_staples"]
    assert settings["theme"] == "dark" and settings["default_servings"] == 4
    assert settings["ingredient_exclusions"] == ["mushroom"]
    recipe_id = create(
        client,
        recipe,
        [
            {"name": "soy sauce", "quantity": 20, "unit": "ml"},
            {"name": "chicken", "quantity": 100, "unit": "g"},
        ],
    )
    response = client.post(f"/api/recipes/{recipe_id}/shopping", json={})
    assert not any(i["name"] == "soy sauce" and not i["checked"] for i in response.json)


def test_staples_can_be_removed_and_added_manually(client, recipe):
    client.put("/api/settings", json={"shopping_staples": []})
    recipe_id = create(
        client, recipe, [{"name": "salt", "quantity": None, "unit": "to taste"}]
    )
    assert len(client.post(f"/api/recipes/{recipe_id}/shopping", json={}).json) == 1
    client.put("/api/settings", json={"shopping_staples": ["salt"]})
    assert (
        len(
            client.post(
                "/api/shopping", json={"name": "salt", "quantity": 500, "unit": "g"}
            ).json
        )
        == 2
    )
    assert (
        "salt"
        in client.get("/api/export?backup=true").json["settings"]["shopping_staples"]
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"include_staples": "false"},
        {"include_optional": "yes"},
        {"servings": 0},
        {"shopping_staples": ["salt"]},
    ],
)
def test_invalid_shopping_options_are_rejected_without_writes(client, recipe, payload):
    recipe_id = create(client, recipe, recipe["ingredients"])
    assert (
        client.post(f"/api/recipes/{recipe_id}/shopping", json=payload).status_code
        == 422
    )
    assert client.get("/api/shopping").json == []


def test_optional_ingredients_remain_optional_when_restoking_staples(client, recipe):
    recipe_id = create(
        client, recipe, [{"name": "salt", "quantity": 1, "unit": "g", "optional": True}]
    )
    assert (
        client.post(
            f"/api/recipes/{recipe_id}/shopping", json={"include_staples": True}
        ).json
        == []
    )
    assert (
        len(
            client.post(
                f"/api/recipes/{recipe_id}/shopping",
                json={"include_staples": True, "include_optional": True},
            ).json
        )
        == 1
    )
