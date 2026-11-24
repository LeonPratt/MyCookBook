# REST API

All API routes begin `/api`. Request and response bodies use JSON, except multipart image uploads. No authentication is provided; deploy only on a trusted LAN. Inputs are validated with Pydantic, unknown recipe fields are rejected, and database access uses SQLAlchemy parameterization. Errors use `{ "error": "message", "details": [{"field":"…", "message":"…"}] }` (details only on schema errors). Statuses: 200 success, 201 created, 204 deleted, 400 invalid JSON or untrusted Host, 403 cross-origin request rejected, 404 missing resource, 409 unavailable optional feature, 413 request too large, 422 validation failure, 502 upstream extraction failure.

Browser API requests must use the same Origin (scheme, host and effective port). Foreign or null Origin headers are rejected; state-changing requests also check Fetch Metadata and fall back to Referer validation if Origin is absent. No cross-origin CORS permissions are granted. Headerless scripts/CLI clients remain supported. Hosts are limited to localhost, private/link-local IP literals and exact extra names configured through `COOKBOOK_ALLOWED_HOSTS`. These controls mitigate browser cross-origin requests and DNS rebinding; they do not replace authentication against a device directly on the LAN.

| Method / route | Behavior |
| --- | --- |
| GET `/health` | Database connectivity check |
| GET `/recipes` | Recipe summaries with personal metadata and cooking counts |
| POST `/recipes` | Validated recipe content; returns new record |
| GET `/recipes/{id}` | Full recipe including history |
| PUT `/recipes/{id}` | Replace validated recipe content, retain personal data |
| DELETE `/recipes/{id}` | Delete recipe and its cooking history |
| POST `/recipes/{id}/duplicate` | Copy content; reset personal data/history |
| PATCH `/recipes/{id}/personal` | Partial personal fields: favourite, feedback, rating, notes, would_cook_again, selected_servings |
| POST `/recipes/{id}/history` | `{servings, cooked_at?, rating?, notes?}`; ISO date/datetime, UTC normalized |
| GET `/history` | Recent meals including recipe titles |
| DELETE `/history/{id}` | Remove one meal record |
| GET `/shopping` | Persisted list |
| POST `/shopping` | `{name, quantity?, unit?, preparation?, category?, checked?}` |
| POST `/recipes/{id}/shopping` | `{servings?, include_optional?: false, include_staples?: false, exclude_ingredient_indices?: []}`; aggregate scaled ingredients, skipping checked ingredient rows (zero-based indices) and saved cupboard staples by default. Indices must be integers within the recipe's ingredient list. |
| POST `/shopping/{id}/staple` | Save the item's ingredient name to cupboard staples and remove its matching unchecked shopping entries; returns updated shopping list |
| PATCH `/shopping/{id}` | `{checked: boolean}` |
| DELETE `/shopping/{id}` | Remove item |
| DELETE `/shopping/completed` | Clear checked items |
| GET/PUT `/settings` | Preferences; PUT excludes read-only `llm_configured` |
| GET `/recommendations` | Explainable ranked recipes; shared filters plus options below |
| POST `/pantry` | `{ingredients: ["lemon", "chicken"]}`; matched/missing names and coverage. Saved cupboard staples are automatically available using full normalized names; optional ingredients do not count toward coverage. |
| GET `/export` | Versioned collection; `?backup=true` includes personal data, settings, shopping |
| GET `/recipes/{id}/export` | Single recipe in a collection envelope |
| POST `/import/preview` | `{data: objectOrArray}`; validation, existing duplicate candidates and earlier matching `duplicate_indices` within this batch, no writes |
| POST `/import` | `{data, actions?: {"0":"skip|separate|replace"}, renames?: {"0":"New unique name"}, restore_personal?:false, restore_settings?:false}` |
| POST `/import/text` | `{text, use_llm?:false}`; validated extraction, never saves |
| POST `/images` | multipart `image` JPEG/PNG/WebP; validates/re-encodes and returns safe local image_path |
| POST/DELETE `/demo` | Load/remove marked demonstration recipes |

`GET /recipes` supports `q` (all terms), `ingredient`, `cuisine`, `category`, `difficulty`, `equipment`, `max_time` (total minutes), `favourite=true`, `feedback=positive|negative|neutral`, `cooked=true|false`, and `sort=recent|alphabetical|cooked|rating|quickest|frequent`. Text filters are case-insensitive substrings. Search covers title, description, ingredient names, cuisine, category and tags. Summary quantities always contain originals.

Recommendations accept the same filters plus `exclude_disliked=true`, `include_cooked=true`, `prioritise_favourites=true`, `not_recent=true`, and `surprise=false`. Settings exclusions/equipment are applied first. Score = rating (or 0), minus 10 for disliked, plus 10 for a prioritised favourite, plus up to 9 for days since cooked (90 days or never cooked). Ties sort by title. Surprise selects up to three randomly from the top 20; regular suggestions return up to six. Dietary exclusions use documented ingredient keyword sets for vegetarian/vegan/dairy-free/gluten-free plus tag matches; this is a convenience filter, not allergen certification.

Import validates the entire input and all final names before mutation. New recipes import automatically; duplicate names default to skip. Titles match exactly after trimming leading/trailing whitespace and ignoring case; punctuation and word order remain significant. This also detects repeated names within a batch. Keeping both (`separate`) requires a `renames` entry with a different, unique name (1–200 characters) that conflicts with neither saved recipes nor another new recipe in the batch. Replace requires exactly one existing match and preserves personal data/history even during restoration. A conflict that arises after preview returns 422 without importing any recipes.

The regular import UI imports recipes only and does not offer backup restoration. The API retains explicit `restore_personal`/`restore_settings` options for backward compatibility: new records can restore personal metadata/history when explicitly requested, and `restore_settings` replaces settings and shopping only when the payload includes a versioned backup. Use the archive restore script for exact database/photo recovery.

Examples:

```json
{"favourite":true,"feedback":"positive","rating":5,"selected_servings":3}
```

PATCH this to `/api/recipes/1/personal`. To clear a rating send `{"rating":null}`; feedback neutral is separate from favourites. Import action indexes refer to the ordered preview, and the original data must be submitted again with decisions.

Settings include `shopping_staples`, an array of up to 200 ingredient names (200 characters each). Blank names are removed and case-insensitive duplicates are collapsed. Default values are salt, sea salt, table salt, black pepper and ground black pepper. Recipe shopping additions compare full normalized names; recommendation exclusions are independent. `include_staples: true` bypasses staple filtering for that addition, and manual additions always remain available. Optional ingredients still require `include_optional: true`. Saving a staple preserves other preferences and purchased shopping entries. Backup exports/restores carry this setting; older settings receive the defaults without a database migration.
