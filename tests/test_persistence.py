import io
import sqlite3
import zipfile
import pytest
from flask_migrate import upgrade
from cookbook import create_app
from cookbook.models import db
from scripts.backup import backup
from scripts.restore import restore


def test_migration_restart_and_archive_roundtrip(tmp_path, monkeypatch, recipe):
    monkeypatch.setenv("COOKBOOK_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(
        "COOKBOOK_DATABASE_URL", "sqlite:///" + str(tmp_path / "data" / "cookbook.db")
    )
    app = create_app({"TESTING": True})
    with app.app_context():
        upgrade()
    client = app.test_client()
    recipe_id = client.post("/api/recipes", json=recipe).json["id"]
    client.patch(
        f"/api/recipes/{recipe_id}/personal",
        json={"selected_servings": 3, "rating": 5, "notes": "Keep me"},
    )
    client.post(
        f"/api/recipes/{recipe_id}/history",
        json={"servings": 3, "cooked_at": "2026-01-01"},
    )
    client.put("/api/settings", json={"theme": "dark", "default_servings": 4})
    client.post(f"/api/recipes/{recipe_id}/shopping", json={"servings": 3})
    first = client.get("/api/shopping").json[0]
    client.patch(f"/api/shopping/{first['id']}", json={"checked": True})
    image_name = "a" * 32 + ".jpg"
    (tmp_path / "data" / "uploads" / image_name).write_bytes(b"test photo bytes")
    archive = backup(tmp_path / "backup.zip")
    # Fresh application factory/engine reads existing persisted records.
    restarted_app = create_app({"TESTING": True})
    restarted = restarted_app.test_client()
    assert (
        restarted.get(f"/api/recipes/{recipe_id}").json["personal"]["selected_servings"]
        == 3
    )
    assert restarted.get("/api/settings").json["theme"] == "dark"
    client.delete(f"/api/recipes/{recipe_id}")
    client.delete("/api/shopping/completed")
    # Stop all application connections before replacing a database on Windows.
    for running_app in [app, restarted_app]:
        with running_app.app_context():
            db.session.remove()
            db.engine.dispose()
    restore(archive, replace=True)
    restored = create_app({"TESTING": True}).test_client()
    row = restored.get(f"/api/recipes/{recipe_id}").json
    assert row["personal"]["notes"] == "Keep me"
    assert row["times_cooked"] == 1
    assert row["ingredients"][0]["quantity"] == 300
    assert restored.get("/api/shopping").json[0]["checked"] is True
    assert restored.get("/api/settings").json["default_servings"] == 4
    assert (tmp_path / "data" / "cookbook.pre-restore.db").exists()
    assert restored.get("/uploads/" + image_name).data == b"test photo bytes"
    with pytest.raises(ValueError, match="already exists"):
        restore(archive, replace=True)


def test_archive_rejects_unsafe_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("COOKBOOK_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(
        "COOKBOOK_DATABASE_URL", "sqlite:///" + str(tmp_path / "data" / "cookbook.db")
    )
    archive = tmp_path / "malicious.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("cookbook.db", b"bad")
        z.writestr("../evil.txt", b"bad")
    with pytest.raises(ValueError, match="unsafe path"):
        restore(archive, replace=True)
    assert not (tmp_path / "evil.txt").exists()


def test_json_restore_keeps_checked_and_unchecked_separate(client, recipe):
    payload = {
        "schema_version": 1,
        "kind": "backup",
        "recipes": [recipe],
        "settings": {},
        "shopping": [
            {"name": "lemon", "quantity": 1, "unit": "", "checked": False},
            {"name": "lemon", "quantity": 2, "unit": "", "checked": True},
        ],
    }
    assert (
        client.post(
            "/api/import", json={"data": payload, "restore_settings": True}
        ).status_code
        == 200
    )
    rows = client.get("/api/shopping").json
    assert len(rows) == 2
    assert rows[0]["checked"] is False and rows[1]["checked"] is True
    assert rows[0]["quantity"] == 1 and rows[1]["quantity"] == 2


@pytest.mark.parametrize("history", [None, 42, ["invalid"]])
def test_malformed_import_history_returns_validation_error(client, recipe, history):
    payload = {**recipe, "history": history}
    assert client.post("/api/import/preview", json={"data": payload}).status_code == 422
    assert client.post("/api/import", json={"data": payload}).status_code == 422
    assert client.get("/api/recipes").json == []
