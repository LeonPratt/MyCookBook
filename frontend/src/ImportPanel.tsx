import { useState } from "react";
import { api } from "./api";
import { Recipe, RecipeContent } from "./types";
type Preview = {
  index: number;
  recipe: RecipeContent;
  duplicates: Recipe[];
  duplicate_indices?: number[];
};
const isDuplicate = (row: Preview) =>
  row.duplicates.length > 0 || (row.duplicate_indices?.length ?? 0) > 0;
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
    [renames, setRenames] = useState<Record<string, string>>({});
  const needsName = (row: Preview) =>
    isDuplicate(row) && actions[row.index] === "separate";
  const invalidName = (row: Preview) =>
    needsName(row) &&
    (!renames[row.index]?.trim() ||
      renames[row.index].trim().toLowerCase() === row.recipe.title.trim().toLowerCase());
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
      setRenames({});
      setActions(
        Object.fromEntries(
          result.map((r) => [
            r.index,
            isDuplicate(r) ? "skip" : "separate",
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
        renames: Object.fromEntries(
          preview.filter(needsName).map((row) => [row.index, renames[row.index].trim()]),
        ),
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
          JSON
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
              ? "Import one recipe or a collection. New recipes are added automatically after review; matching names need your decision."
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
              {isDuplicate(row) ? <>
              <p role="alert">
                Duplicate name detected: “{row.recipe.title}” already exists
                {row.duplicates.length ? " in your cookbook." : " in this import."}
              </p>
              <label>
                Import action
                <select
                  value={actions[row.index]}
                  onChange={(e) =>
                    setActions({ ...actions, [row.index]: e.target.value })
                  }
                >
                  <option value="separate">Keep both (rename imported recipe)</option>
                  <option value="skip">Skip</option>
                  {row.duplicates.length === 1 && (
                    <option value="replace">
                      Replace existing recipe content
                    </option>
                  )}
                </select>
              </label>
              {needsName(row) && (
                <label>
                  New name for imported recipe
                  <input
                    value={renames[row.index] ?? ""}
                    maxLength={200}
                    required
                    aria-invalid={invalidName(row)}
                    onChange={(e) => setRenames({ ...renames, [row.index]: e.target.value })}
                  />
                  {invalidName(row) && <small>Enter a different, unique recipe name.</small>}
                </label>
              )}
              </> : <p>Will be imported as a new recipe.</p>}
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
          <p className="small-text muted">
            This imports recipes only. For a complete backup restore including
            personal data, settings, shopping lists and photos, use the archive
            restore script.
          </p>
          <div className="form-actions">
            <button className="button secondary" onClick={() => setPreview([])}>
              Back
            </button>
            <button
              className="button"
              disabled={busy || preview.some(invalidName)}
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
