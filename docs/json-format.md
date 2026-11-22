# JSON format, version 1

Collections use `{ "schema_version": 1, "kind": "collection", "recipes": [...] }`. Exports add `exported_at`. Import also accepts a single bare recipe object or array. Unknown recipe content fields and unsupported envelope versions are rejected. Full content constraints are defined in [recipe.schema.json](recipe.schema.json), generated from the actual validation model.

```json
{
  "schema_version": 1,
  "kind": "collection",
  "recipes": [{
    "title": "Lemon pasta",
    "description": "A quick lunch.",
    "servings": 2,
    "prep_time": 5,
    "cook_time": 15,
    "total_time": null,
    "difficulty": "Easy",
    "cuisine": "Italian",
    "category": "Lunch",
    "tags": ["Quick"],
    "equipment": ["Hob", "Saucepan/pot"],
    "equipment_alternatives": [],
    "ingredients": [
      {"name":"pasta","quantity":200,"unit":"g","preparation":"","optional":false,"group":"","category":"Pantry"},
      {"name":"lemon","quantity":0.5,"unit":"","preparation":"juiced","optional":false,"group":"Sauce","category":"Produce"},
      {"name":"salt","quantity":null,"unit":"to taste","optional":true}
    ],
    "instructions": [{"text":"Cook the pasta and toss with lemon.","timer_seconds":900}],
    "image_path": "",
    "source": "Personal recipe",
    "demo": false
  }]
}
```

Only title, nonempty ingredients and nonempty instructions are required. The default serving count is 2. Quantities use JSON numbers (fractional decimal values allowed), or null for nonnumeric amounts. Never put `"1/2"` in the quantity field; use `0.5`. Display can show familiar fractions. A text quantity such as “to taste” can be retained in unit or preparation. Ordered ingredient groups use the `group` field; step ordering follows the array. Timers are optional seconds. Time fields are minutes. Image paths must reference generated local uploads (`/uploads/<32-hex-id>.jpg|png|webp`); external URLs and arbitrary filesystem paths are rejected.

Personal backup exports use `kind: "backup"`. Recipe records add a `personal` object, `history` array, IDs, creation/modification timestamps and computed history counts. Personal fields are favourite (boolean), feedback (`positive`, `negative`, `neutral`), rating (null or integer 1–5), notes, would_cook_again (null/boolean), selected_servings (null/positive number). History entries contain cooked_at, servings, optional rating and notes. New IDs/timestamps are assigned on JSON import; history IDs are regenerated. Replace keeps existing personal fields/history. The envelope also includes settings and shopping arrays; the explicit restoration checkbox enables those fields.

Recipe content exports omit personal data/history. Neither export embeds photos or API credentials. Archive backups are the complete, lossless database-and-photo transfer format. Keep the same schema version for backwards-compatible optional additions; use a new version and conversion path for breaking changes.
