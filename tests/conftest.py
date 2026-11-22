import pytest
from cookbook import create_app
from cookbook.models import db


@pytest.fixture
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.db"),
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        }
    )
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def recipe():
    return {
        "title": "Lemon chicken",
        "description": "Weeknight dinner",
        "servings": 2,
        "prep_time": 10,
        "cook_time": 20,
        "cuisine": "Italian",
        "category": "Dinner",
        "tags": ["Quick"],
        "equipment": ["Hob"],
        "ingredients": [
            {"name": "chicken breast", "quantity": 300, "unit": "g"},
            {"name": "lemon", "quantity": 0.5, "unit": ""},
            {"name": "salt", "quantity": None, "unit": "to taste"},
        ],
        "instructions": [{"text": "Cook chicken thoroughly.", "timer_seconds": 180}],
    }
