import { useState } from "react";
import { api } from "./api";
import { Recipe, RecipeContent } from "./types";
type Preview = { index: number; recipe: RecipeContent; duplicates: Recipe[] };
export default function ImportPanel({
  llm,
  onRecipe,
  onDone,
  onError,
}: {
  llm: boolean;
  onRecipe: (r: RecipeContent) => void;
  onDone: () => void;
  onError: (e: unknown) => void;
}) {
  const [mode, setMode] = useState("json"),
    [text, setText] = useState(""),
    [useLLM, setUseLLM] = useState(false),
    [preview, setPreview] = useState<Preview[]>([]),
    [data, setData] = useState<unknown>(null),
    [actions, setActions] = useState<Record<string, string>>({}),
    [busy, setBusy] = useState(false),
    [restore, setRestore] = useState(false);
  const review = async () => {
    setBusy(true);
    try {
      if (mode === "text") {
        onRecipe(
          await api<RecipeContent>("/import/text", "POST", {
            text,
            use_llm: useLLM,
          }),
        );
        return;
      }
      const parsed = JSON.parse(text);
      const result = await api<Preview[]>("/import/preview", "POST", {
        data: parsed,
      });
      setData(parsed);
      setPreview(result);
      setActions(
        Object.fromEntries(
          result.map((r) => [
            r.index,
            r.duplicates.length ? "skip" : "separate",
          ]),
        ),
      );
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  };
  const save = async () => {
    setBusy(true);
    try {
      await api("/import", "POST", {
        data,
        actions,
        restore_personal: restore,
        restore_settings: restore,
      });
      onDone();
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="import-panel">
      <div className="segmented">
        <button
          className={mode === "json" ? "active" : ""}
          onClick={() => {
            setMode("json");
            setPreview([]);
          }}
        >
          JSON / backup
        </button>
        <button
          className={mode === "text" ? "active" : ""}
          onClick={() => {
            setMode("text");
            setPreview([]);
          }}
        >
          Paste recipe text
        </button>
      </div>
      {preview.length === 0 ? (
        <>
          <p className="muted">
            {mode === "json"
              ? "Import one recipe, a collection, or a MyCookBook backup. You’ll review duplicates before saving."
              : "Paste a title, Servings: line, Ingredients heading and Method or Instructions heading. Missing quantities stay blank. You can edit the extraction before saving."}
          </p>
          {mode === "json" && (
            <label className="upload-label">
              Choose a JSON file
              <input
                type="file"
                accept="application/json,.json"
                onChange={async (e) => {
                  try {
                    const file = e.target.files?.[0];
                    if (file) {
                      if (file.size > 8 * 1024 * 1024)
                        throw new Error("Choose a file smaller than 8 MB");
                      setText(await file.text());
                    }
                  } catch (e) {
                    onError(e);
                  }
                }}
              />
            </label>
          )}
          <label>
            {mode === "json" ? "Recipe JSON" : "Recipe text"}
            <textarea
              rows={13}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={
                mode === "json"
                  ? "Paste JSON here…"
                  : "Lemon pasta\nServings: 2\nPrep time: 10 minutes\nIngredients\n200 g pasta\n1 lemon\nInstructions\n1. Cook the pasta.\n2. Toss with lemon and serve."
              }
            />
          </label>
          {mode === "text" && (
            <label className="inline-check">
              <input
                type="checkbox"
                checked={useLLM}
                disabled={!llm}
                onChange={(e) => setUseLLM(e.target.checked)}
              />
              {llm
                ? "Use configured LLM (sends pasted text to your configured endpoint)"
                : "Optional LLM is not configured — local parser available"}
            </label>
          )}
          <button
            className="button"
            disabled={busy || !text.trim()}
            onClick={() => void review()}
          >
            {busy ? "Reading recipe…" : "Review import"}
          </button>
        </>
      ) : (
        <>
          <p>
            {preview.length} {preview.length === 1 ? "recipe" : "recipes"} ready
            for review. Existing personal feedback and cooking history are
            retained when replacing content.
          </p>
          {preview.map((row) => (
            <div className="import-review" key={row.index}>
              <h3>{row.recipe.title}</h3>
              <p>
                {row.recipe.ingredients.length} ingredients ·{" "}
                {row.recipe.servings} portions
              </p>
              <label>
                Import action
                <select
                  value={actions[row.index]}
                  onChange={(e) =>
                    setActions({ ...actions, [row.index]: e.target.value })
                  }
                >
                  <option value="separate">Import as separate recipe</option>
                  <option value="skip">Skip</option>
                  {row.duplicates.length === 1 && (
                    <option value="replace">
                      Replace existing recipe content
                    </option>
                  )}
                </select>
              </label>
              {row.duplicates.map((d) => (
                <details key={d.id}>
                  <summary>Compare with “{d.title}”</summary>
                  <table>
                    <thead>
                      <tr>
                        <th>Field</th>
                        <th>Existing</th>
                        <th>Imported</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.keys(row.recipe)
                        .filter((k) => k !== "demo")
                        .map((k) => (
                          <tr key={k}>
                            <th>{k.replaceAll("_", " ")}</th>
                            <td>{JSON.stringify(d[k as keyof Recipe])}</td>
                            <td>
                              {JSON.stringify(
                                row.recipe[k as keyof RecipeContent],
                              )}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </details>
              ))}
            </div>
          ))}
          <label className="inline-check">
            <input
              type="checkbox"
              checked={restore}
              onChange={(e) => setRestore(e.target.checked)}
            />
            Restore personal metadata for new recipes, plus settings and
            shopping list from backup
          </label>
          <p className="small-text muted">
            For a complete replacement restore including photos, use the archive
            backup script. This JSON import merges recipes; restoring settings
            replaces your shopping list.
          </p>
          <div className="form-actions">
            <button className="button secondary" onClick={() => setPreview([])}>
              Back
            </button>
            <button
              className="button"
              disabled={busy}
              onClick={() => void save()}
            >
              {busy ? "Importing…" : "Import selected recipes"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
