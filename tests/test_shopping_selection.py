import pytest


def test_checked_rows_are_skipped_before_scaling_and_aggregation(client, recipe):
    recipe["ingredients"] = [
        {"name": "chicken", "quantity": 300, "unit": "g"},
        {"name": "chicken", "quantity": 100, "unit": "g", "preparation": "diced"},
        {"name": "salt", "quantity": None, "unit": "to taste"},
        {"name": "lemon", "quantity": 1, "optional": True},
    ]
    saved = client.post("/api/recipes", json=recipe).json
    client.post("/api/shopping", json={"name": "chicken", "quantity": 50, "unit": "g"})
    response = client.post(
        f"/api/recipes/{saved['id']}/shopping",
        json={
            "servings": 3,
            "include_optional": True,
            "include_staples": True,
            "exclude_ingredient_indices": [0, 2, 3],
        },
    )
    assert response.status_code == 201
    assert len(response.json) == 1
    assert response.json[0]["name"] == "chicken"
    assert response.json[0]["quantity"] == 200  # Existing 50 + unchecked 100 * 3/2.
    assert client.get(f"/api/recipes/{saved['id']}").json == saved
    before = response.json
    response = client.post(
        f"/api/recipes/{saved['id']}/shopping",
        json={"exclude_ingredient_indices": [0, 1, 2, 3]},
    )
    assert response.status_code == 201
    assert response.json == before


@pytest.mark.parametrize("indices", [[-1], [3], [0, 99], [1.5], ["0"], [True], None])
def test_invalid_exclusions_reject_without_adding_anything(client, recipe, indices):
    recipe_id = client.post("/api/recipes", json=recipe).json["id"]
    response = client.post(
        f"/api/recipes/{recipe_id}/shopping",
        json={"exclude_ingredient_indices": indices},
    )
    assert response.status_code == 422
    assert client.get("/api/shopping").json == []
