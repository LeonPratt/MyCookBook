def test_staples_complete_matches_and_update_when_removed(client, recipe):
    saved = client.post("/api/recipes", json=recipe).json
    response = client.post("/api/pantry", json={"ingredients": ["chicken", "lemon"]})
    assert response.status_code == 200
    assert response.json[0]["matched"] == ["chicken breast", "lemon", "salt"]
    assert response.json[0]["missing"] == []
    assert response.json[0]["coverage"] == 1

    client.put("/api/settings", json={"shopping_staples": []})
    result = client.post("/api/pantry", json={"ingredients": ["chicken", "lemon"]}).json
    assert result[0]["missing"] == ["salt"]
    assert result[0]["coverage"] == 2 / 3
    assert client.get(f"/api/recipes/{saved['id']}").json == saved


def test_staples_match_full_normalized_names_without_broadening_to_similar_foods(
    client, recipe
):
    recipe["ingredients"] = [
        {"name": name} for name in ["SOY-SAUCE", "dark soy sauce", "chickpeas", "rice"]
    ]
    recipe["ingredients"].append({"name": "lemon", "optional": True})
    client.post("/api/recipes", json=recipe)
    client.put("/api/settings", json={"shopping_staples": ["soy sauce", "chickpea"]})
    row = client.post("/api/pantry", json={"ingredients": ["rice"]}).json[0]
    assert row["matched"] == ["SOY-SAUCE", "chickpeas", "rice"]
    assert row["missing"] == ["dark soy sauce"]
    assert row["coverage"] == 0.75


def test_staples_are_available_without_typing_and_contribute_to_ranking(client, recipe):
    for title, ingredients in [
        ("Needs chicken", [{"name": "salt"}, {"name": "chicken"}]),
        ("Ready now", [{"name": "salt"}]),
        ("No matches", [{"name": "rice"}]),
    ]:
        client.post("/api/recipes", json={**recipe, "title": title, "ingredients": ingredients})
    rows = client.post("/api/pantry", json={"ingredients": []}).json
    assert [row["title"] for row in rows] == ["Ready now", "Needs chicken"]
    assert [row["coverage"] for row in rows] == [1, 0.5]
    assert rows[1]["missing"] == ["chicken"]
