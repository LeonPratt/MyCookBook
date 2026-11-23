import math
from datetime import datetime, timezone
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Schema(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, allow_inf_nan=False
    )


class Ingredient(Schema):
    name: str = Field(min_length=1, max_length=200)
    quantity: float | None = Field(default=None, ge=0, le=1e9)
    unit: str = Field(default="", max_length=60)
    preparation: str = Field(default="", max_length=300)
    optional: bool = False
    group: str = Field(default="", max_length=100)
    category: str = Field(default="Other", max_length=100)


class Step(Schema):
    text: str = Field(min_length=1, max_length=10000)
    timer_seconds: int | None = Field(default=None, ge=1, le=86400)


class RecipeInput(Schema):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    servings: float = Field(default=2, gt=0, le=1000)
    prep_time: int = Field(default=0, ge=0, le=10080)
    cook_time: int = Field(default=0, ge=0, le=10080)
    total_time: int | None = Field(default=None, ge=0, le=20160)
    difficulty: Literal["Easy", "Medium", "Hard"] = "Easy"
    cuisine: str = Field(default="", max_length=100)
    category: str = Field(default="", max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=50)
    ingredients: list[Ingredient] = Field(min_length=1, max_length=500)
    instructions: list[Step] = Field(min_length=1, max_length=200)
    equipment: list[str] = Field(default_factory=list, max_length=50)
    equipment_alternatives: list[str] = Field(default_factory=list, max_length=50)
    image_path: str = Field(default="", max_length=500)
    source: str = Field(default="", max_length=2000)
    demo: bool = False

    @field_validator("image_path")
    @classmethod
    def safe_image(cls, value):
        import re

        if value and not re.fullmatch(r"/uploads/[a-f0-9]{32}\.(jpg|png|webp)", value):
            raise ValueError("Image must be a local uploaded image path")
        return value


class Personal(Schema):
    favourite: bool = False
    feedback: Literal["positive", "negative", "neutral"] = "neutral"
    rating: int | None = Field(default=None, ge=1, le=5)
    notes: str = Field(default="", max_length=20000)
    would_cook_again: bool | None = None
    selected_servings: float | None = Field(default=None, gt=0, le=1000)


class HistoryInput(Schema):
    cooked_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    servings: float = Field(gt=0, le=1000)
    rating: int | None = Field(default=None, ge=1, le=5)
    notes: str = Field(default="", max_length=20000)

    @field_validator("cooked_at")
    @classmethod
    def valid_date(cls, value):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()


class ShoppingInput(Ingredient):
    checked: bool = False


class RecipeShoppingInput(Schema):
    servings: float | None = Field(default=None, gt=0, le=1000)
    include_optional: bool = Field(default=False, strict=True)
    include_staples: bool = Field(default=False, strict=True)
    exclude_ingredient_indices: list[Annotated[int, Field(strict=True, ge=0)]] = Field(
        default_factory=list, max_length=500
    )


class SettingsInput(Schema):
    default_servings: float = Field(default=2, gt=0, le=1000)
    theme: Literal["light", "dark", "system"] = "system"
    equipment: list[str] = Field(
        default_factory=lambda: ["Hob", "Frying pan", "Saucepan/pot", "Oven"]
    )
    dietary_exclusions: list[str] = Field(default_factory=list, max_length=100)
    ingredient_exclusions: list[str] = Field(default_factory=list, max_length=100)
    shopping_staples: list[str] = Field(
        default_factory=lambda: [
            "salt",
            "sea salt",
            "table salt",
            "black pepper",
            "ground black pepper",
        ],
        max_length=200,
    )

    @field_validator("shopping_staples")
    @classmethod
    def clean_staples(cls, values):
        cleaned = {}
        for value in values:
            name = value.strip()
            if len(name) > 200:
                raise ValueError("Staple names must be at most 200 characters")
            if name:
                cleaned.setdefault(name.casefold(), name)
        return list(cleaned.values())
