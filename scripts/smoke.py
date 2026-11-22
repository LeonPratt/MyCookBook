"""Exercise a release using only temporary data and installed production packages."""

import io
import re
import tempfile
from pathlib import Path

from flask_migrate import upgrade
from PIL import Image

from cookbook import create_app
from cookbook.models import db


def main():
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as temporary:
        config = {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(Path(temporary) / "smoke.db"),
            "UPLOAD_FOLDER": str(Path(temporary) / "uploads"),
        }
        app = create_app(config)
        with app.app_context():
            upgrade(directory=str(root / "migrations"))
        client = app.test_client()
        assert client.get("/api/health").status_code == 200
        recipe = {
            "title": "Temporary deployment verification",
            "servings": 2,
            "ingredients": [{"name": "rice", "quantity": 100, "unit": "g"}],
            "instructions": [{"text": "Cook for 20 minutes.", "timer_seconds": 1200}],
        }
        preview = client.post("/api/import/preview", json={"data": recipe})
        assert preview.status_code == 200 and len(preview.json) == 1
        imported = client.post("/api/import", json={"data": recipe})
        assert imported.status_code == 200 and imported.json["imported"] == 1
        saved = client.get("/api/recipes").json[0]
        recipe_id = saved["id"]
        assert (
            client.patch(
                f"/api/recipes/{recipe_id}/personal", json={"selected_servings": 3}
            ).status_code
            == 200
        )
        shopping = client.post(
            f"/api/recipes/{recipe_id}/shopping", json={"servings": 3}
        )
        assert shopping.status_code == 201 and shopping.json[0]["quantity"] == 150
        assert (
            client.get(f"/api/recipes/{recipe_id}").json["ingredients"][0]["quantity"]
            == 100
        )
        assert (
            client.get(f"/api/recipes/{recipe_id}").json["instructions"][0][
                "timer_seconds"
            ]
            == 1200
        )
        assert (
            client.post(
                f"/api/recipes/{recipe_id}/history", json={"servings": 3}
            ).status_code
            == 201
        )
        assert (
            client.post(
                "/api/import", json={"data": client.get("/api/export?backup=true").json}
            ).json["imported"]
            == 0
        )
        photo = io.BytesIO()
        Image.new("RGB", (10, 10)).save(photo, "PNG")
        photo.seek(0)
        uploaded = client.post("/api/images", data={"image": (photo, "test.png")})
        assert (
            uploaded.status_code == 201
            and client.get(uploaded.json["image_path"]).status_code == 200
        )
        page = client.get("/")
        assert page.status_code == 200
        assets = re.findall(
            r'(?:src|href)="(/assets/[^\"]+)"', page.get_data(as_text=True)
        )
        assert assets and all(client.get(asset).status_code == 200 for asset in assets)
        assert (
            client.post(
                "/api/demo", headers={"Origin": "https://foreign.invalid"}
            ).status_code
            == 403
        )
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
        restarted = create_app(config)
        persisted = restarted.test_client().get(f"/api/recipes/{recipe_id}")
        assert persisted.status_code == 200 and persisted.json["times_cooked"] == 1
        assert persisted.json["personal"]["selected_servings"] == 3
        with restarted.app_context():
            db.session.remove()
            db.engine.dispose()
    print(
        "PASS: migrations, API, JSON import/export, selected portions, scaled shopping, history, photo upload, static assets, origin guards and restart persistence (temporary data only)."
    )


if __name__ == "__main__":
    main()
