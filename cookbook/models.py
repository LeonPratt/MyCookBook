from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def now():
    return datetime.now(timezone.utc).isoformat()


class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.JSON, nullable=False)
    personal = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.String, nullable=False, default=now)
    updated_at = db.Column(db.String, nullable=False, default=now)
    history = db.relationship(
        "CookingSession",
        cascade="all, delete-orphan",
        backref="recipe",
        lazy="selectin",
    )


class CookingSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(
        db.Integer, db.ForeignKey("recipe.id"), nullable=False, index=True
    )
    cooked_at = db.Column(db.String, nullable=False)
    servings = db.Column(db.Float, nullable=False)
    rating = db.Column(db.Integer)
    notes = db.Column(db.Text, nullable=False, default="")


class ShoppingItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    quantity = db.Column(db.Float)
    unit = db.Column(db.String, nullable=False, default="")
    preparation = db.Column(db.String, nullable=False, default="")
    category = db.Column(db.String, nullable=False, default="Other")
    checked = db.Column(db.Boolean, nullable=False, default=False)


class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True, default=1)
    data = db.Column(db.JSON, nullable=False, default=dict)
