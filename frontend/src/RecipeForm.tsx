import { useState } from "react";
import { Plus, Trash2, Upload } from "lucide-react";
import { api } from "./api";
import {
  Recipe,
  RecipeContent,
  emptyIngredient,
  equipmentOptions,
  contentOnly,
} from "./types";

export default function RecipeForm({
  initial,
  onSave,
  onCancel,
  onError,
}: {
  initial: RecipeContent;
  onSave: (r: Recipe) => void;
  onCancel: () => void;
  onError: (e: unknown) => void;
}) {
  const [form, setForm] = useState<RecipeContent>(contentOnly(initial)),
    [busy, setBusy] = useState(false);
  const set = <K extends keyof RecipeContent>(
    key: K,
    value: RecipeContent[K],
  ) => setForm((f) => ({ ...f, [key]: value }));
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const id = (initial as Recipe).id;
      const r = await api<Recipe>(
        id ? `/recipes/${id}` : "/recipes",
        id ? "PUT" : "POST",
        form,
      );
      onSave(r);
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  };
  const upload = async (file?: File) => {
    if (!file) return;
    setBusy(true);
    try {
      const data = new FormData();
      data.append("image", file);
      set(
        "image_path",
        (await api<{ image_path: string }>("/images", "POST", data)).image_path,
      );
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <form onSubmit={submit} className="recipe-form">
      <div className="form-grid">
        <label className="full">
          Recipe title
          <input
            required
            maxLength={200}
            value={form.title}
            onChange={(e) => set("title", e.target.value)}
            placeholder="What are we cooking?"
          />
        </label>
        <label className="full">
          Description
          <textarea
            value={form.description}
            onChange={(e) => set("description", e.target.value)}
            rows={2}
          />
        </label>
        <label>
          Default portions
          <input
            type="number"
            min="0.1"
            max="1000"
            step="any"
            required
            value={form.servings}
            onChange={(e) => set("servings", Number(e.target.value))}
          />
        </label>
        <label>
          Difficulty
          <select
            value={form.difficulty}
            onChange={(e) =>
              set("difficulty", e.target.value as RecipeContent["difficulty"])
            }
          >
            {["Easy", "Medium", "Hard"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <label>
          Prep time (minutes)
          <input
            type="number"
            min="0"
            value={form.prep_time}
            onChange={(e) => set("prep_time", Number(e.target.value))}
          />
        </label>
        <label>
          Cook time (minutes)
          <input
            type="number"
            min="0"
            value={form.cook_time}
            onChange={(e) => set("cook_time", Number(e.target.value))}
          />
        </label>
        <label>
          Total time (optional)
          <input
            type="number"
            min="0"
            value={form.total_time ?? ""}
            onChange={(e) =>
              set(
                "total_time",
                e.target.value === "" ? null : Number(e.target.value),
              )
            }
          />
        </label>
        <label>
          Cuisine
          <input
            value={form.cuisine}
            onChange={(e) => set("cuisine", e.target.value)}
          />
        </label>
        <label>
          Category
          <input
            value={form.category}
            onChange={(e) => set("category", e.target.value)}
          />
        </label>
        <label>
          Tags (comma separated)
          <input
            value={form.tags.join(", ")}
            onChange={(e) =>
              set(
                "tags",
                e.target.value.split(",").map((v) => v.trim()),
              )
            }
          />
        </label>
        <label className="full">
          Source
          <input
            value={form.source}
            onChange={(e) => set("source", e.target.value)}
            placeholder="Book, author or original URL"
          />
        </label>
      </div>
      <fieldset>
        <legend>Equipment</legend>
        <div className="check-grid">
          {equipmentOptions.map((v) => (
            <label key={v}>
              <input
                type="checkbox"
                checked={form.equipment.includes(v)}
                onChange={(e) =>
                  set(
                    "equipment",
                    e.target.checked
                      ? [...form.equipment, v]
                      : form.equipment.filter((x) => x !== v),
                  )
                }
              />
              {v}
            </label>
          ))}
        </div>
        <label>
          Alternative methods (one per line)
          <textarea
            value={form.equipment_alternatives.join("\n")}
            onChange={(e) =>
              set("equipment_alternatives", e.target.value.split("\n"))
            }
            placeholder="Only add explicitly tested alternatives."
          />
        </label>
      </fieldset>
      <div className="section-heading">
        <h3>Ingredients</h3>
        <button
          type="button"
          className="text-button"
          onClick={() =>
            set("ingredients", [...form.ingredients, emptyIngredient()])
          }
        >
          <Plus size={16} /> Add ingredient
        </button>
      </div>
      {form.ingredients.map((item, i) => (
        <fieldset className="ingredient-editor" key={i}>
          <legend>Ingredient {i + 1}</legend>
          <div className="ingredient-fields">
            <label>
              Name
              <input
                required
                value={item.name}
                onChange={(e) =>
                  set(
                    "ingredients",
                    form.ingredients.map((v, n) =>
                      n === i ? { ...v, name: e.target.value } : v,
                    ),
                  )
                }
              />
            </label>
            <label>
              Quantity
              <input
                type="number"
                min="0"
                step="any"
                placeholder="To taste"
                value={item.quantity ?? ""}
                onChange={(e) =>
                  set(
                    "ingredients",
                    form.ingredients.map((v, n) =>
                      n === i
                        ? {
                            ...v,
                            quantity:
                              e.target.value === ""
                                ? null
                                : Number(e.target.value),
                          }
                        : v,
                    ),
                  )
                }
              />
            </label>
            <label>
              Unit
              <input
                value={item.unit}
                onChange={(e) =>
                  set(
                    "ingredients",
                    form.ingredients.map((v, n) =>
                      n === i ? { ...v, unit: e.target.value } : v,
                    ),
                  )
                }
              />
            </label>
            <button
              type="button"
              className="icon-button danger"
              aria-label={`Remove ingredient ${i + 1}`}
              disabled={form.ingredients.length === 1}
              onClick={() =>
                set(
                  "ingredients",
                  form.ingredients.filter((_, n) => n !== i),
                )
              }
            >
              <Trash2 size={17} />
            </button>
          </div>
          <div className="form-grid">
            <label>
              Preparation
              <input
                value={item.preparation}
                onChange={(e) =>
                  set(
                    "ingredients",
                    form.ingredients.map((v, n) =>
                      n === i ? { ...v, preparation: e.target.value } : v,
                    ),
                  )
                }
                placeholder="Diced, drained…"
              />
            </label>
            <label>
              Group
              <input
                value={item.group}
                onChange={(e) =>
                  set(
                    "ingredients",
                    form.ingredients.map((v, n) =>
                      n === i ? { ...v, group: e.target.value } : v,
                    ),
                  )
                }
                placeholder="Sauce, topping…"
              />
            </label>
            <label>
              Shopping category
              <input
                value={item.category}
                onChange={(e) =>
                  set(
                    "ingredients",
                    form.ingredients.map((v, n) =>
                      n === i ? { ...v, category: e.target.value } : v,
                    ),
                  )
                }
              />
            </label>
            <label className="inline-check">
              <input
                type="checkbox"
                checked={item.optional}
                onChange={(e) =>
                  set(
                    "ingredients",
                    form.ingredients.map((v, n) =>
                      n === i ? { ...v, optional: e.target.checked } : v,
                    ),
                  )
                }
              />
              Optional ingredient
            </label>
          </div>
        </fieldset>
      ))}
      <div className="section-heading">
        <h3>Method</h3>
        <button
          type="button"
          className="text-button"
          onClick={() =>
            set("instructions", [
              ...form.instructions,
              { text: "", timer_seconds: null },
            ])
          }
        >
          <Plus size={16} /> Add step
        </button>
      </div>
      {form.instructions.map((step, i) => (
        <fieldset key={i}>
          <legend>Step {i + 1}</legend>
          <label>
            Instruction
            <textarea
              required
              rows={3}
              value={step.text}
              onChange={(e) =>
                set(
                  "instructions",
                  form.instructions.map((s, n) =>
                    n === i ? { ...s, text: e.target.value } : s,
                  ),
                )
              }
            />
          </label>
          <div className="row">
            <label>
              Timer (seconds, optional)
              <input
                type="number"
                min="1"
                max="86400"
                value={step.timer_seconds ?? ""}
                onChange={(e) =>
                  set(
                    "instructions",
                    form.instructions.map((s, n) =>
                      n === i
                        ? {
                            ...s,
                            timer_seconds:
                              e.target.value === ""
                                ? null
                                : Number(e.target.value),
                          }
                        : s,
                    ),
                  )
                }
              />
            </label>
            <button
              className="icon-button danger"
              aria-label={`Remove step ${i + 1}`}
              type="button"
              disabled={form.instructions.length === 1}
              onClick={() =>
                set(
                  "instructions",
                  form.instructions.filter((_, n) => n !== i),
                )
              }
            >
              <Trash2 size={18} />
            </button>
          </div>
        </fieldset>
      ))}
      <label className="upload-label">
        <Upload size={18} />{" "}
        {form.image_path ? "Replace recipe photo" : "Upload a recipe photo"}
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(e) => void upload(e.target.files?.[0])}
        />
      </label>
      {form.image_path && (
        <div className="row">
          <img
            className="upload-preview"
            src={form.image_path}
            alt="Recipe preview"
          />
          <button
            type="button"
            className="text-button"
            onClick={() => set("image_path", "")}
          >
            Remove photo
          </button>
        </div>
      )}
      <div className="form-actions">
        <button type="button" className="button secondary" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="button" disabled={busy}>
          {busy ? "Saving…" : "Save recipe"}
        </button>
      </div>
    </form>
  );
}
