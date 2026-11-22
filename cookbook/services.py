"""Pure quantities, deterministic extraction, matching and versioned transfers."""

import json
import math
import re
from fractions import Fraction
from .schemas import RecipeInput, Personal, HistoryInput
from .models import Recipe, CookingSession, ShoppingItem, Setting, db, now

SCHEMA_VERSION = 1
CONTENT_KEYS = set(RecipeInput.model_fields)


def normalise(value):
    value = re.sub(r"[^a-z0-9 ]", " ", value.lower())
    value = " ".join(value.split())
    aliases = {
        "scallions": "spring onion",
        "scallion": "spring onion",
        "garbanzo beans": "chickpea",
        "chickpeas": "chickpea",
        "bell peppers": "pepper",
        "bell pepper": "pepper",
        "courgettes": "courgette",
        "zucchini": "courgette",
        "tomatoes": "tomato",
        "potatoes": "potato",
        "onions": "onion",
        "eggs": "egg",
        "mushrooms": "mushroom",
        "chicken breasts": "chicken breast",
    }
    return aliases.get(value.strip(), " ".join(value.split()))


def matches(a, b):
    a, b = normalise(a), normalise(b)
    return bool(a and b) and (
        a == b
        or set(a.split()).issubset(b.split())
        or set(b.split()).issubset(a.split())
    )


def serialize_history(h):
    return dict(
        id=h.id,
        recipe_id=h.recipe_id,
        cooked_at=h.cooked_at,
        servings=h.servings,
        rating=h.rating,
        notes=h.notes,
    )


def serialize(r, include_history=True):
    history = sorted(r.history, key=lambda h: h.cooked_at, reverse=True)
    result = {
        **r.content,
        "id": r.id,
        "personal": Personal.model_validate(r.personal).model_dump(),
        "created_at": r.created_at,
        "updated_at": r.updated_at,
        "times_cooked": len(history),
        "last_cooked": history[0].cooked_at if history else None,
    }
    if include_history:
        result["history"] = [serialize_history(h) for h in history]
    return result


def compatible_quantity(quantity, unit):
    unit = unit.lower().strip()
    aliases = {
        "grams": "g",
        "gram": "g",
        "kilograms": "kg",
        "kilogram": "kg",
        "millilitres": "ml",
        "milliliter": "ml",
        "litres": "l",
        "liter": "l",
        "teaspoon": "tsp",
        "teaspoons": "tsp",
        "tablespoon": "tbsp",
        "tablespoons": "tbsp",
    }
    unit = aliases.get(unit, unit)
    if unit == "kg":
        return quantity * 1000 if quantity is not None else None, "g"
    if unit == "l":
        return quantity * 1000 if quantity is not None else None, "ml"
    return quantity, unit


def add_shopping(ingredient, scale=1):
    quantity = ingredient.get("quantity")
    quantity, unit = compatible_quantity(
        quantity * scale if quantity is not None else None, ingredient.get("unit", "")
    )
    # Shopping totals describe what to buy; slicing/dicing stays in each recipe.
    # Checked items are already purchased and must not absorb new requirements.
    existing = []
    if quantity is not None and not ingredient.get("checked", False):
        existing = [
            i
            for i in db.session.scalars(
                db.select(ShoppingItem)
                .where(ShoppingItem.checked.is_(False))
                .order_by(ShoppingItem.id)
            )
            if normalise(i.name) == normalise(ingredient["name"])
            and i.quantity is not None
            and compatible_quantity(i.quantity, i.unit)[1] == unit
        ]
    if existing:
        target = existing[0]
        target.quantity = math.fsum(
            [quantity] + [compatible_quantity(i.quantity, i.unit)[0] for i in existing]
        )
        target.unit = unit
        preparations = [
            part.strip() for i in existing for part in i.preparation.split(";")
        ]
        preparations += [
            part.strip() for part in ingredient.get("preparation", "").split(";")
        ]
        target.preparation = "; ".join(dict.fromkeys(p for p in preparations if p))
        if target.category == "Other" and ingredient.get("category"):
            target.category = ingredient["category"]
        for duplicate in existing[1:]:
            db.session.delete(duplicate)
    else:
        db.session.add(
            ShoppingItem(
                name=ingredient["name"],
                quantity=quantity,
                unit=unit,
                preparation=ingredient.get("preparation", ""),
                category=ingredient.get("category", "Other"),
                checked=ingredient.get("checked", False),
            )
        )


def parse_quantity(value):
    value = value.strip()
    for char, replacement in {
        "½": " 1/2",
        "¼": " 1/4",
        "¾": " 3/4",
        "⅓": " 1/3",
        "⅔": " 2/3",
        "⅛": " 1/8",
    }.items():
        value = value.replace(char, replacement)
    return float(sum(Fraction(part) for part in value.split()))


def parse_text(text):
    lines = [
        line.strip().strip("*").strip() for line in text.splitlines() if line.strip()
    ]
    result = dict(
        title="Imported recipe",
        ingredients=[],
        instructions=[],
        description="",
        tags=[],
        equipment=[],
    )
    section = "header"
    descriptions = []
    for line in lines:
        clean = re.sub(r"^#+\s*", "", line).strip()
        heading = clean.rstrip(":").lower()
        if heading in ["ingredients", "ingredient list"]:
            section = "ingredients"
            continue
        if heading in ["instructions", "method", "directions", "steps"]:
            section = "instructions"
            continue
        meta = re.match(
            r"^(servings|serves|portions|prep(?:aration)? time|cook(?:ing)? time|total time|tags|equipment|cuisine|category|difficulty)\s*[:=]?\s+(.+)$",
            clean,
            re.I,
        )
        if meta and section == "header":
            key, value = meta.group(1).lower(), meta.group(2)
            if key in ["servings", "serves", "portions"]:
                number = re.search(r"\d+(?:\.\d+)?", value)
                if number:
                    result["servings"] = float(number[0])
            elif "time" in key:
                hours = re.search(r"(\d+)\s*(?:hours?|hrs?|h)\b", value, re.I)
                minutes = re.search(r"(\d+)\s*(?:minutes?|mins?|m)\b", value, re.I)
                duration = (int(hours[1]) * 60 if hours else 0) + (
                    int(minutes[1]) if minutes else 0
                )
                if not hours and not minutes:
                    number = re.search(r"\d+", value)
                    duration = int(number[0]) if number else 0
                result[
                    "prep_time"
                    if key.startswith("prep")
                    else "cook_time"
                    if key.startswith("cook")
                    else "total_time"
                ] = duration
            elif key in ["tags", "equipment"]:
                result[key] = [v.strip() for v in value.split(",") if v.strip()]
            else:
                result[key] = value.title() if key == "difficulty" else value
            continue
        if section == "header":
            if result["title"] == "Imported recipe":
                result["title"] = clean
            else:
                descriptions.append(clean)
        elif section == "ingredients":
            clean = re.sub(r"^[-•*]\s*", "", clean)
            match = re.match(
                r"^((?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?[½¼¾⅓⅔⅛]?|[½¼¾⅓⅔⅛]))\s*(.*)$",
                clean,
            )
            item = dict(name=clean, quantity=None, unit="")
            if match:
                remainder = match[2]
                unit = re.match(
                    r"^(kg|g|ml|l|tsp|tbsp|cups?|cloves?|cans?|tins?|grams?|kilograms?|millilitres?|litres?|teaspoons?|tablespoons?)\b\s*(.*)",
                    remainder,
                    re.I,
                )
                item.update(
                    quantity=parse_quantity(match[1]),
                    name=(unit[2] if unit else remainder).strip(),
                    unit=unit[1].lower() if unit else "",
                )
            result["ingredients"].append(item)
        else:
            clean = re.sub(r"^(?:\d+[.)]|[-•*])\s*", "", clean)
            result["instructions"].append({"text": clean})
    result["description"] = " ".join(descriptions)
    # No guesses about absent quantities, temperatures or timers.
    return RecipeInput.model_validate(result).model_dump()


def transfer_records(payload):
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict) and "recipes" in payload:
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Unsupported schema_version; expected 1")
        records = payload["recipes"]
    else:
        records = [payload]
    if not isinstance(records, list) or not records or len(records) > 2000:
        raise ValueError("Import must contain between 1 and 2000 recipes")
    validated = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Every recipe must be an object")
        unknown = (
            set(record)
            - CONTENT_KEYS
            - {
                "id",
                "personal",
                "history",
                "created_at",
                "updated_at",
                "times_cooked",
                "last_cooked",
            }
        )
        if unknown:
            raise ValueError("Unknown recipe fields: " + ", ".join(sorted(unknown)))
        content = RecipeInput.model_validate(
            {k: v for k, v in record.items() if k in CONTENT_KEYS}
        ).model_dump()
        personal = Personal.model_validate(record.get("personal", {})).model_dump()
        raw_history = record.get("history", [])
        if not isinstance(raw_history, list) or not all(
            isinstance(h, dict) for h in raw_history
        ):
            raise ValueError(
                "Recipe history must be an array of cooking session objects"
            )
        history = [
            HistoryInput.model_validate(
                {k: v for k, v in h.items() if k not in ["id", "recipe_id"]}
            ).model_dump()
            for h in raw_history
        ]
        validated.append(dict(content=content, personal=personal, history=history))
    return validated


def duplicates(content):
    return [
        r
        for r in db.session.scalars(db.select(Recipe))
        if normalise(r.content["title"]) == normalise(content["title"])
    ]


def import_records(records, actions, restore_personal=False):
    # Validation and duplicate decisions happen before any database write.
    decisions = []
    seen = set()
    for index, record in enumerate(records):
        candidates = duplicates(record["content"])
        title = normalise(record["content"]["title"])
        action = actions.get(
            str(index), "skip" if candidates or title in seen else "separate"
        )
        if action not in ["skip", "separate", "replace"]:
            raise ValueError("Import action must be skip, separate or replace")
        if action == "replace" and len(candidates) != 1:
            raise ValueError("Replace requires exactly one matching existing recipe")
        decisions.append((record, action, candidates))
        seen.add(title)
    count = 0
    for record, action, candidates in decisions:
        if action == "skip":
            continue
        if action == "replace":
            recipe = candidates[0]
            recipe.content = record["content"]
            recipe.updated_at = now()
        else:
            recipe = Recipe(
                content=record["content"],
                personal=record["personal"]
                if restore_personal
                else Personal().model_dump(),
            )
            db.session.add(recipe)
            db.session.flush()
            if restore_personal:
                for h in record["history"]:
                    db.session.add(CookingSession(recipe_id=recipe.id, **h))
        count += 1
    return count
