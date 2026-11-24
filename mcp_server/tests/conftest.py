from pathlib import Path
from unittest.mock import patch

import pytest
from flask_migrate import upgrade

from cookbook import create_app
from cookbook.models import db
from mcp_server.config import Config


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("COOKBOOK_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("COOKBOOK_DATABASE_URL", "sqlite:///" + str(tmp_path / "cookbook.db"))
    app = create_app({"TESTING": True, "UPLOAD_FOLDER": str(tmp_path / "uploads")})
    with app.app_context():
        # Alembic's fileConfig otherwise disables pytest's capture/audit loggers.
        with patch("logging.config.fileConfig"):
            upgrade(directory=str(Path(__file__).resolve().parents[2] / "migrations"))
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def config():
    return Config(token="test-token-" + "x" * 40, recipe_base_url="http://localhost:5432")


@pytest.fixture
def server(app, config):
    from mcp_server.server import create_server

    return create_server(config, app)


@pytest.fixture
def recipe():
    return {
        "title": "Lemon chicken", "servings": 2, "cuisine": "Italian", "category": "Dinner",
        "tags": ["Weeknight"], "source": "Family notes", "equipment": ["Hob"],
        "equipment_alternatives": ["Use the explicit oven method"], "total_time": 30,
        "ingredients": [
            {"name": "chicken breast", "quantity": 300, "unit": "g", "group": "Main", "preparation": "diced"},
            {"name": "lemon", "quantity": 0.5, "optional": True},
            {"name": "salt", "quantity": None},
        ],
        "instructions": [{"text": "Cook thoroughly.", "timer_seconds": 180}],
    }
