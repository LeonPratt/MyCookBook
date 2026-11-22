import { useState, useEffect } from "react";
import {
  Heart,
  ThumbsUp,
  ThumbsDown,
  Clock3,
  ChefHat,
  ShoppingBasket,
  Play,
  Pencil,
  Copy,
  Trash2,
  Download,
  Check,
  X,
} from "lucide-react";
import { api, formatQuantity } from "./api";
import { Recipe, Personal } from "./types";
import { FoodArt, Portions, Stars, Timer, Modal } from "./components";

type Props = {
  recipe: Recipe;
  onUpdate: (r: Recipe) => void;
  onEdit: () => void;
  onBack: () => void;
  notify: (m: string) => void;
  onError: (e: unknown) => void;
};
export default function RecipeDetail({
  recipe: r,
  onUpdate,
  onEdit,
  onBack,
  notify,
  onError,
}: Props) {
  const [servings, setServings] = useState(
      r.personal.selected_servings ?? r.servings,
    ),
    [checked, setChecked] = useState<number[]>([]),
    [notes, setNotes] = useState(r.personal.notes),
    [cooking, setCooking] = useState(false),
    [log, setLog] = useState(false),
    [deleting, setDeleting] = useState(false),
    [optional, setOptional] = useState(false),
    [includeStaples, setIncludeStaples] = useState(false);
  useEffect(() => {
    setNotes(r.personal.notes);
  }, [r.personal.notes]);
  const feedback = async (data: Partial<Personal>) => {
    try {
      onUpdate(await api<Recipe>(`/recipes/${r.id}/personal`, "PATCH", data));
      return true;
    } catch (e) {
      onError(e);
      return false;
    }
  };
  const portions = (v: number) => {
    setServings(v);
    void feedback({ selected_servings: v });
  };
  const checklist = (
    <div className="ingredients">
      {r.ingredients.map((i, n) => (
        <div key={n}>
          {i.group && (n === 0 || r.ingredients[n - 1].group !== i.group) && (
            <h4>{i.group}</h4>
          )}
          <label className={checked.includes(n) ? "checked" : ""}>
            <input
              type="checkbox"
              checked={checked.includes(n)}
              onChange={(e) =>
                setChecked(
                  e.target.checked
                    ? [...checked, n]
                    : checked.filter((v) => v !== n),
                )
              }
            />
            <span>
              <strong>
                {formatQuantity(i.quantity, servings, r.servings)} {i.unit}
              </strong>{" "}
              {i.name}
              {i.preparation && <small>, {i.preparation}</small>}
              {i.optional && <small> (optional)</small>}
            </span>
          </label>
        </div>
      ))}
    </div>
  );
  if (cooking)
    return (
      <Cooking
        recipe={r}
        servings={servings}
        onPortions={portions}
        checklist={checklist}
        onExit={() => setCooking(false)}
        onFinish={() => {
          setCooking(false);
          setLog(true);
        }}
      />
    );
  return (
    <div className="detail">
      <button className="text-button back-link" onClick={onBack}>
        Back to recipes
      </button>
      <div className="detail-hero">
        <FoodArt recipe={r} large />
        <div className="detail-intro">
          <div className="eyebrow">
            {r.cuisine || "Your kitchen"} · {r.category}
          </div>
          <h1>{r.title}</h1>
          <p>{r.description}</p>
          <div className="recipe-meta">
            <span>
              <Clock3 size={17} />
              {r.prep_time} min prep
            </span>
            <span>{r.cook_time} min cook</span>
            <span>
              <ChefHat size={17} />
              {r.difficulty}
            </span>
          </div>
          <div className="tags">
            {r.tags.map((t) => (
              <span key={t}>{t}</span>
            ))}
          </div>
          <div className="row feedback">
            <button
              className={
                "button secondary " + (r.personal.favourite ? "selected" : "")
              }
              onClick={() =>
                void feedback({ favourite: !r.personal.favourite })
              }
            >
              <Heart
                size={18}
                fill={r.personal.favourite ? "currentColor" : "none"}
              />
              {r.personal.favourite ? "Saved favourite" : "Favourite"}
            </button>
            <button
              className={
                "icon-button " +
                (r.personal.feedback === "positive" ? "selected" : "")
              }
              aria-label="Like recipe"
              aria-pressed={r.personal.feedback === "positive"}
              onClick={() =>
                void feedback({
                  feedback:
                    r.personal.feedback === "positive" ? "neutral" : "positive",
                })
              }
            >
              <ThumbsUp size={19} />
            </button>
            <button
              className={
                "icon-button " +
                (r.personal.feedback === "negative" ? "selected" : "")
              }
              aria-label="Dislike recipe"
              aria-pressed={r.personal.feedback === "negative"}
              onClick={() =>
                void feedback({
                  feedback:
                    r.personal.feedback === "negative" ? "neutral" : "negative",
                })
              }
            >
              <ThumbsDown size={19} />
            </button>
            <Stars
              value={r.personal.rating}
              onChange={(rating) => void feedback({ rating })}
            />
          </div>
          <button className="button" onClick={() => setCooking(true)}>
            <Play size={17} /> Start cooking
          </button>
        </div>
      </div>
      <div className="detail-columns">
        <aside>
          <section className="panel">
            <div className="section-heading">
              <h2>Ingredients</h2>
              <span>{r.ingredients.length} items</span>
            </div>
            <Portions value={servings} onChange={portions} />
            <p className="muted small-text">
              Quantities scale. Times and method stay the same.
            </p>
            {checklist}
            <label className="inline-check">
              <input
                type="checkbox"
                checked={optional}
                onChange={(e) => setOptional(e.target.checked)}
              />
              Include optional ingredients
            </label>
            <label className="inline-check">
              <input
                type="checkbox"
                checked={includeStaples}
                onChange={(e) => setIncludeStaples(e.target.checked)}
              />
              Include cupboard staples this time
            </label>
            <p className="muted small-text">
              Your “Always have” ingredients are skipped by default.{" "}
              <a className="text-button" href="#settings">
                Manage cupboard staples
              </a>
            </p>
            <button
              className="button secondary wide"
              onClick={async () => {
                try {
                  await api(`/recipes/${r.id}/shopping`, "POST", {
                    servings,
                    include_optional: optional,
                    include_staples: includeStaples,
                  });
                  notify("Ingredients added to your shopping list");
                } catch (e) {
                  onError(e);
                }
              }}
            >
              <ShoppingBasket size={17} /> Add to shopping list
            </button>
          </section>
          <section className="panel">
            <h3>Equipment</h3>
            <p>{r.equipment.join(" · ") || "No equipment specified"}</p>
            {r.equipment_alternatives.filter(Boolean).length > 0 && (
              <>
                <h4>Alternative methods</h4>
                {r.equipment_alternatives.map((a, i) => (
                  <p key={i}>{a}</p>
                ))}
              </>
            )}
          </section>
        </aside>
        <div>
          <section className="panel method">
            <h2>Let’s make it</h2>
            {r.instructions.map((step, i) => (
              <div className="method-step" key={i}>
                <span className="step-number">{i + 1}</span>
                <div>
                  <p>{step.text}</p>
                  {step.timer_seconds && <Timer seconds={step.timer_seconds} />}
                </div>
              </div>
            ))}
          </section>
          <section className="panel">
            <div className="section-heading">
              <h2>Your kitchen notes</h2>
              <span>Just for you</span>
            </div>
            <textarea
              rows={4}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="A little more lemon next time? Make this recipe your own."
            />
            <div className="row between">
              <label>
                Would you cook this again?
                <select
                  value={
                    r.personal.would_cook_again === null
                      ? ""
                      : String(r.personal.would_cook_again)
                  }
                  onChange={(e) =>
                    void feedback({
                      would_cook_again:
                        e.target.value === ""
                          ? null
                          : e.target.value === "true",
                    })
                  }
                >
                  <option value="">Not decided</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </label>
              <button
                className="button secondary"
                onClick={async () => {
                  if (await feedback({ notes })) notify("Notes saved");
                }}
              >
                Save notes
              </button>
            </div>
          </section>
          <section className="panel">
            <div className="section-heading">
              <h2>Cooking history</h2>
              <button className="text-button" onClick={() => setLog(true)}>
                Record a meal
              </button>
            </div>
            <p className="muted">
              Cooked {r.times_cooked} {r.times_cooked === 1 ? "time" : "times"}
              {r.last_cooked
                ? " · Last made " + new Date(r.last_cooked).toLocaleDateString()
                : ""}
            </p>
            {r.history?.map((h) => (
              <div className="history-row" key={h.id}>
                <div>
                  <strong>{new Date(h.cooked_at).toLocaleDateString()}</strong>
                  <p>
                    {h.servings} portions
                    {h.rating ? ` · ${h.rating}/5 stars` : ""}
                  </p>
                  <p>{h.notes}</p>
                </div>
                <button
                  className="icon-button danger"
                  aria-label="Delete cooking record"
                  onClick={async () => {
                    try {
                      await api(`/history/${h.id}`, "DELETE");
                      onUpdate(await api<Recipe>(`/recipes/${r.id}`));
                    } catch (e) {
                      onError(e);
                    }
                  }}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </section>
        </div>
      </div>
      <div className="detail-actions">
        <button className="button secondary" onClick={onEdit}>
          <Pencil size={16} /> Edit recipe
        </button>
        <button
          className="button secondary"
          onClick={async () => {
            try {
              const copy = await api<Recipe>(
                `/recipes/${r.id}/duplicate`,
                "POST",
              );
              location.hash = `recipe/${copy.id}`;
              notify("Recipe duplicated");
            } catch (e) {
              onError(e);
            }
          }}
        >
          <Copy size={16} /> Duplicate
        </button>
        <a
          className="button secondary"
          href={`/api/recipes/${r.id}/export`}
          download
        >
          <Download size={16} /> Export JSON
        </a>
        <button
          className="text-button danger"
          onClick={() => setDeleting(true)}
        >
          <Trash2 size={16} /> Delete recipe
        </button>
      </div>
      {r.source && <p className="muted source">Source: {r.source}</p>}
      {log && (
        <Modal title="A meal worth remembering" onClose={() => setLog(false)}>
          <CookingLog
            servings={servings}
            onSave={async (data) => {
              await api(`/recipes/${r.id}/history`, "POST", data);
              onUpdate(await api<Recipe>(`/recipes/${r.id}`));
              setLog(false);
              notify("Meal added to cooking history");
            }}
            onError={onError}
          />
        </Modal>
      )}
      {deleting && (
        <Modal title="Delete this recipe?" onClose={() => setDeleting(false)}>
          <p>
            This removes {r.title} and its cooking history. Export it first if
            you want a copy.
          </p>
          <div className="form-actions">
            <button
              className="button secondary"
              onClick={() => setDeleting(false)}
            >
              Keep recipe
            </button>
            <button
              className="button danger-fill"
              onClick={async () => {
                try {
                  await api(`/recipes/${r.id}`, "DELETE");
                  onBack();
                  notify("Recipe deleted");
                } catch (e) {
                  onError(e);
                }
              }}
            >
              Delete recipe
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function CookingLog({
  servings,
  onSave,
  onError,
}: {
  servings: number;
  onSave: (v: unknown) => Promise<void>;
  onError: (e: unknown) => void;
}) {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10)),
    [portions, setPortions] = useState(servings),
    [rating, setRating] = useState<number | null>(null),
    [notes, setNotes] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        try {
          await onSave({ cooked_at: date, servings: portions, rating, notes });
        } catch (e) {
          onError(e);
        } finally {
          setBusy(false);
        }
      }}
    >
      <label>
        Date cooked
        <input
          type="date"
          required
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
      </label>
      <Portions value={portions} onChange={setPortions} />
      <label>How was it?</label>
      <Stars value={rating} onChange={setRating} />
      <label>
        Notes
        <textarea
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </label>
      <button className="button" disabled={busy}>
        <Check size={17} />
        {busy ? "Saving…" : "Record cooked meal"}
      </button>
    </form>
  );
}

function Cooking({
  recipe: r,
  servings,
  onPortions,
  checklist,
  onExit,
  onFinish,
}: {
  recipe: Recipe;
  servings: number;
  onPortions: (n: number) => void;
  checklist: React.ReactNode;
  onExit: () => void;
  onFinish: () => void;
}) {
  const [step, setStep] = useState(0),
    [showIngredients, setShowIngredients] = useState(false),
    [wake, setWake] = useState(false);
  useEffect(() => {
    let lock: WakeLockSentinel | null = null;
    let active = true;
    const acquire = async () => {
      try {
        if ("wakeLock" in navigator && document.visibilityState === "visible") {
          lock = await navigator.wakeLock.request("screen");
          if (!active) {
            await lock.release();
            return;
          }
          setWake(true);
          lock.addEventListener("release", () => setWake(false));
        }
      } catch {
        setWake(false);
      }
    };
    void acquire();
    const visible = () => {
      if (document.visibilityState === "visible") void acquire();
    };
    document.addEventListener("visibilitychange", visible);
    return () => {
      active = false;
      document.removeEventListener("visibilitychange", visible);
      void lock?.release();
    };
  }, []);
  return (
    <div className="cooking-mode">
      <header>
        <div>
          <span className="eyebrow">Cooking mode</span>
          <h2>{r.title}</h2>
        </div>
        <button className="button secondary" onClick={onExit}>
          <X size={16} /> Exit
        </button>
      </header>
      <div
        className="cooking-progress"
        role="progressbar"
        aria-valuenow={step + 1}
        aria-valuemin={1}
        aria-valuemax={r.instructions.length}
      >
        <span
          style={{ width: `${((step + 1) / r.instructions.length) * 100}%` }}
        />
      </div>
      <div className="cooking-controls">
        <Portions value={servings} onChange={onPortions} />
        <button
          className="text-button"
          onClick={() => setShowIngredients(!showIngredients)}
        >
          {showIngredients ? "Hide" : "Show"} ingredients
        </button>
      </div>
      {showIngredients && <section className="panel">{checklist}</section>}
      <div className="cooking-step">
        <p className="eyebrow">
          Step {step + 1} of {r.instructions.length}
        </p>
        <p>{r.instructions[step].text}</p>
        {r.instructions[step].timer_seconds && (
          <Timer key={step} seconds={r.instructions[step].timer_seconds!} />
        )}
      </div>
      <div className="row between">
        <button
          className="button secondary"
          disabled={step === 0}
          onClick={() => setStep(step - 1)}
        >
          Previous step
        </button>
        {step === r.instructions.length - 1 ? (
          <button className="button" onClick={onFinish}>
            <Check size={18} /> Finish cooking
          </button>
        ) : (
          <button className="button" onClick={() => setStep(step + 1)}>
            Next step
          </button>
        )}
      </div>
      <p className="muted small-text">
        {wake
          ? "Screen stays awake while cooking."
          : "Keep your screen awake in device settings if needed. Screen wake lock requires a supported browser and secure connection."}
      </p>
    </div>
  );
}
