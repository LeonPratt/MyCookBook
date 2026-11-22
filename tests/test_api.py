import copy
import io
import pytest
from PIL import Image
from cookbook.services import parse_text, parse_quantity


def create(client, recipe):
    response = client.post("/api/recipes", json=recipe)
    assert response.status_code == 201, response.json
    return response.json


def test_recipe_lifecycle_and_validation(client, recipe):
    r = create(client, recipe)
    assert r["personal"]["feedback"] == "neutral"
    updated = {**recipe, "title": "New title"}
    assert (
        client.put(f"/api/recipes/{r['id']}", json=updated).json["title"] == "New title"
    )
    assert (
        client.post("/api/recipes", json={**recipe, "servings": 0}).status_code == 422
    )
    assert (
        client.post("/api/recipes", json={**recipe, "unknown": True}).status_code == 422
    )
    assert (
        client.post("/api/recipes", json={**recipe, "ingredients": []}).status_code
        == 422
    )
    assert client.delete(f"/api/recipes/{r['id']}").status_code == 204
    assert client.get(f"/api/recipes/{r['id']}").status_code == 404


def test_feedback_history_and_duplicate(client, recipe):
    r = create(client, recipe)
    path = f"/api/recipes/{r['id']}"
    result = client.patch(
        path + "/personal",
        json={
            "favourite": True,
            "feedback": "negative",
            "rating": 4,
            "notes": "More lemon",
            "would_cook_again": False,
            "selected_servings": 3,
        },
    )
    assert result.json["personal"]["favourite"] is True
    assert result.json["personal"]["feedback"] == "negative"
    assert result.json["ingredients"][0]["quantity"] == 300
    assert client.patch(path + "/personal", json={"rating": 6}).status_code == 422
    assert client.patch(path + "/personal", json={"rating": 4.5}).status_code == 422
    h = client.post(
        path + "/history",
        json={"servings": 3, "cooked_at": "2026-01-01", "notes": "Tasty"},
    ).json
    assert client.get(path).json["times_cooked"] == 1
    assert client.get("/api/history").json[0]["title"] == recipe["title"]
    assert client.post(path + "/history", json={"servings": -1}).status_code == 422
    assert (
        client.post(
            path + "/history", json={"servings": 2, "cooked_at": "yesterday"}
        ).status_code
        == 422
    )
    duplicate = client.post(path + "/duplicate").json
    assert duplicate["personal"]["notes"] == ""
    assert duplicate["times_cooked"] == 0
    assert client.delete(f"/api/history/{h['id']}").status_code == 204
    assert client.get(path).json["times_cooked"] == 0
    assert (
        client.patch(
            path + "/personal",
            json={"rating": None, "feedback": "neutral", "favourite": False},
        ).json["personal"]["rating"]
        is None
    )


@pytest.mark.parametrize(
    "query,expected",
    [
        ("q=chicken", 1),
        ("q=weeknight", 1),
        ("q=lemon", 1),
        ("q=italian", 1),
        ("q=quick", 1),
        ("q=absent", 0),
        ("equipment=Hob", 1),
        ("max_time=29", 0),
        ("max_time=30", 1),
        ("favourite=true", 0),
        ("cooked=false", 1),
        ("cooked=true", 0),
        ("difficulty=Hard", 0),
        ("ingredient=lemon", 1),
    ],
)
def test_search(client, recipe, query, expected):
    create(client, recipe)
    assert len(client.get("/api/recipes?" + query).json) == expected


def test_sort_and_invalid_filter(client, recipe):
    create(client, {**recipe, "title": "Z dish", "cook_time": 5})
    create(client, {**recipe, "title": "A dish", "cook_time": 10})
    assert client.get("/api/recipes?sort=alphabetical").json[0]["title"] == "A dish"
    assert client.get("/api/recipes?sort=quickest").json[0]["title"] == "Z dish"
    assert client.get("/api/recipes?max_time=notanumber").status_code == 422


def test_scaled_shopping_safe_aggregation(client, recipe):
    r = create(client, recipe)
    client.post(f"/api/recipes/{r['id']}/shopping", json={"servings": 3, "include_staples": True})
    rows = client.get("/api/shopping").json
    assert rows[0]["quantity"] == 450
    assert rows[1]["quantity"] == 0.75
    assert rows[2]["quantity"] is None
    client.post(
        "/api/shopping", json={"name": "chicken breast", "quantity": 0.5, "unit": "kg"}
    )
    assert client.get("/api/shopping").json[0]["quantity"] == 950
    client.post(
        "/api/shopping", json={"name": "chicken breast", "quantity": 2, "unit": "tsp"}
    )
    assert len(client.get("/api/shopping").json) == 4
    first = rows[0]["id"]
    assert (
        client.patch(f"/api/shopping/{first}", json={"checked": "yes"}).status_code
        == 422
    )
    client.patch(f"/api/shopping/{first}", json={"checked": True})
    client.delete("/api/shopping/completed")
    assert len(client.get("/api/shopping").json) == 3
    assert (
        client.get(f"/api/recipes/{r['id']}").json["ingredients"][0]["quantity"] == 300
    )


def test_import_roundtrip_duplicates_and_preservation(client, recipe):
    r = create(client, recipe)
    path = f"/api/recipes/{r['id']}"
    client.patch(
        path + "/personal", json={"notes": "Keep this", "rating": 5, "favourite": True}
    )
    client.post(path + "/history", json={"servings": 2})
    exported = client.get("/api/export?backup=true").json
    preview = client.post("/api/import/preview", json={"data": exported}).json
    assert preview[0]["duplicates"][0]["id"] == r["id"]
    assert client.post("/api/import", json={"data": exported}).json["imported"] == 0
    changed = copy.deepcopy(exported)
    changed["recipes"][0]["description"] = "Replaced content"
    response = client.post(
        "/api/import",
        json={"data": changed, "actions": {"0": "replace"}, "restore_personal": True},
    )
    assert response.status_code == 200, response.json
    result = client.get(path).json
    assert result["description"] == "Replaced content"
    assert result["personal"]["notes"] == "Keep this"
    assert result["times_cooked"] == 1
    assert (
        client.post(
            "/api/import",
            json={
                "data": exported,
                "actions": {"0": "separate"},
                "restore_personal": True,
            },
        ).json["imported"]
        == 1
    )
    assert len(client.get("/api/recipes").json) == 2
    client.delete(path)
    other = client.get("/api/recipes").json[0]
    client.delete(f"/api/recipes/{other['id']}")
    assert (
        client.post(
            "/api/import",
            json={"data": exported, "restore_personal": True, "restore_settings": True},
        ).status_code
        == 200
    )
    result = client.get("/api/recipes").json[0]
    assert result["personal"]["rating"] == 5
    assert result["times_cooked"] == 1


def test_import_atomic_and_schema_errors(client, recipe):
    assert (
        client.post(
            "/api/import", json={"data": [recipe, {**recipe, "servings": 0}]}
        ).status_code
        == 422
    )
    assert client.get("/api/recipes").json == []
    assert (
        client.post(
            "/api/import", json={"data": {"schema_version": 42, "recipes": [recipe]}}
        ).status_code
        == 422
    )
    assert (
        client.post("/api/import", json={"data": {**recipe, "typo": True}}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/import", json={"data": [recipe], "actions": {"0": "replace"}}
        ).status_code
        == 422
    )
    assert (
        client.post("/api/import", json={"data": [recipe, recipe]}).json["imported"]
        == 1
    )


def test_pantry_and_recommendation_preferences(client, recipe):
    r = create(client, recipe)
    pantry = client.post("/api/pantry", json={"ingredients": ["chicken", "lemon"]}).json
    assert pantry[0]["coverage"] == pytest.approx(2 / 3)
    assert pantry[0]["missing"] == ["salt"]
    assert client.post("/api/pantry", json={"ingredients": [12]}).status_code == 422
    assert len(client.get("/api/recommendations").json) == 1
    client.patch(f"/api/recipes/{r['id']}/personal", json={"feedback": "negative"})
    assert client.get("/api/recommendations").json == []
    assert len(client.get("/api/recommendations?exclude_disliked=false").json) == 1
    client.put("/api/settings", json={"ingredient_exclusions": ["chicken"]})
    assert client.get("/api/recommendations?exclude_disliked=false").json == []
    client.put("/api/settings", json={"equipment": ["Oven"]})
    assert client.get("/api/recommendations?exclude_disliked=false").json == []
    client.put("/api/settings", json={"dietary_exclusions": ["Vegetarian"]})
    assert client.get("/api/recommendations?exclude_disliked=false").json == []


def test_text_parser_quantities_and_no_invention(client):
    text = "Lemon pasta\nServes: 2\nPrep time: 1 hour 10 minutes\nTags: vegetarian, quick\nEquipment: Hob\nIngredients\n- 1 1/2 tbsp olive oil\n- ½ lemon\n- salt to taste\nInstructions\n1. Toss everything together."
    response = client.post("/api/import/text", json={"text": text})
    assert response.status_code == 200, response.json
    r = response.json
    assert r["ingredients"][0]["quantity"] == 1.5
    assert r["ingredients"][1]["quantity"] == 0.5
    assert r["ingredients"][2]["quantity"] is None
    assert r["prep_time"] == 70
    assert client.get("/api/recipes").json == []
    assert parse_quantity("2½") == 2.5
    assert (
        client.post(
            "/api/import/text", json={"text": "No ingredient sections"}
        ).status_code
        == 422
    )


def test_images_and_path_security(client, recipe):
    image = io.BytesIO()
    Image.new("RGB", (20, 20), color="green").save(image, "PNG")
    image.seek(0)
    response = client.post("/api/images", data={"image": (image, "../../evil.png")})
    assert response.status_code == 201
    path = response.json["image_path"]
    assert ".." not in path
    assert client.get(path).status_code == 200
    assert (
        client.post(
            "/api/images",
            data={"image": (io.BytesIO(b"<script>bad</script>"), "bad.jpg")},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/recipes", json={**recipe, "image_path": "https://evil.test/a.jpg"}
        ).status_code
        == 422
    )
    assert client.get("/uploads/../../requirements.txt").status_code == 404
    assert client.get("/api/unknown").status_code == 404


def test_demo_lifecycle(client):
    assert client.post("/api/demo").status_code == 200
    assert len(client.get("/api/recipes").json) == 6
    client.post("/api/demo")
    assert len(client.get("/api/recipes").json) == 6
    client.delete("/api/demo")
    assert client.get("/api/recipes").json == []
