from cookbook.models import db, ShoppingItem


def test_same_ingredient_stacks_across_recipe_preparations(client, recipe):
    for quantity, preparation in [(300, "sliced"), (400, "diced")]:
        content = {
            **recipe,
            "ingredients": [
                {
                    "name": "chicken breast",
                    "quantity": quantity,
                    "unit": "g",
                    "preparation": preparation,
                }
            ],
        }
        created = client.post("/api/recipes", json=content)
        assert created.status_code == 201
        response = client.post(
            f"/api/recipes/{created.json['id']}/shopping", json={"servings": 2}
        )
        assert response.status_code == 201
    rows = client.get("/api/shopping").json
    assert len(rows) == 1
    assert rows[0]["quantity"] == 700
    assert rows[0]["unit"] == "g"
    assert rows[0]["preparation"] == "sliced; diced"
    recipes = client.get("/api/recipes").json
    assert sorted(r["ingredients"][0]["quantity"] for r in recipes) == [300, 400]


def test_manual_addition_merges_case_aliases_units_and_preparations(client):
    for name, quantity, unit, preparation in [
        ("Chicken breasts", 300, "grams", "sliced"),
        (" chicken  breast ", 0.4, "kg", ""),
        ("CHICKEN BREAST", 100, "g", "diced"),
    ]:
        assert (
            client.post(
                "/api/shopping",
                json={
                    "name": name,
                    "quantity": quantity,
                    "unit": unit,
                    "preparation": preparation,
                },
            ).status_code
            == 201
        )
    rows = client.get("/api/shopping").json
    assert len(rows) == 1
    assert rows[0]["quantity"] == 800
    assert rows[0]["preparation"] == "sliced; diced"


def test_addition_consolidates_all_legacy_matching_rows(app, client):
    with app.app_context():
        db.session.add_all(
            [
                ShoppingItem(
                    name="chicken breast", quantity=300, unit="g", preparation="sliced"
                ),
                ShoppingItem(
                    name="chicken breast", quantity=0.4, unit="kg", preparation="diced"
                ),
            ]
        )
        db.session.commit()
    client.post(
        "/api/shopping",
        json={
            "name": "chicken breast",
            "quantity": 100,
            "unit": "gram",
            "preparation": "sliced",
        },
    )
    rows = client.get("/api/shopping").json
    assert len(rows) == 1
    assert rows[0]["quantity"] == 800
    assert rows[0]["unit"] == "g"
    assert rows[0]["preparation"] == "sliced; diced"


def test_purchased_unknown_and_incompatible_ingredients_remain_separate(client):
    for item in [
        {"name": "chicken breast", "quantity": 300, "unit": "g", "checked": True},
        {"name": "chicken breast", "quantity": 400, "unit": "g"},
        {"name": "chicken breast", "quantity": 1, "unit": ""},
        {"name": "chicken thigh", "quantity": 200, "unit": "g"},
        {"name": "chicken breast", "quantity": None, "unit": "g"},
    ]:
        assert client.post("/api/shopping", json=item).status_code == 201
    rows = client.get("/api/shopping").json
    assert len(rows) == 5
    assert sorted(
        i["quantity"]
        for i in rows
        if i["name"] == "chicken breast" and i["quantity"] is not None
    ) == [1, 300, 400]
