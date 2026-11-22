import { useState, useEffect, useCallback } from "react";
import {
  BookOpen,
  Heart,
  Sparkles,
  ShoppingBasket,
  History,
  Settings as SettingsIcon,
  Search,
  Plus,
  SlidersHorizontal,
  Upload,
  Leaf,
  X,
  Trash2,
  Check,
  Download,
  ChefHat,
  Menu,
} from "lucide-react";
import { api, formatQuantity } from "./api";
import {
  Recipe,
  RecipeContent,
  Settings,
  Shopping,
  Session,
  emptyRecipe,
  equipmentOptions,
} from "./types";
import { RecipeCard, Modal } from "./components";
import RecipeForm from "./RecipeForm";
import RecipeDetail from "./RecipeDetail";
import ImportPanel from "./ImportPanel";

const navigation = [
  ["recipes", "Recipes", BookOpen],
  ["favourites", "Favourites", Heart],
  ["discover", "What should I cook?", Sparkles],
  ["shopping", "Shopping list", ShoppingBasket],
  ["history", "Cooking history", History],
  ["settings", "Settings", SettingsIcon],
] as const;
const defaultSettings: Settings = {
  default_servings: 2,
  theme: "system",
  equipment: [],
  dietary_exclusions: [],
  ingredient_exclusions: [],
  shopping_staples: [
    "salt",
    "sea salt",
    "table salt",
    "black pepper",
    "ground black pepper",
  ],
};
export default function App() {
  const [route, setRoute] = useState(location.hash.slice(1) || "recipes"),
    [recipes, setRecipes] = useState<Recipe[]>([]),
    [selected, setSelected] = useState<Recipe | null>(null),
    [settings, setSettings] = useState<Settings>(defaultSettings),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [toast, setToast] = useState(""),
    [refresh, setRefresh] = useState(0),
    [form, setForm] = useState<RecipeContent | null>(null),
    [importing, setImporting] = useState(false),
    [mobileMenu, setMobileMenu] = useState(false);
  const [search, setSearch] = useState(""),
    [filters, setFilters] = useState<Record<string, string>>({
      sort: "recent",
    }),
    [showFilters, setShowFilters] = useState(false);
  const notify = useCallback((m: string) => setToast(m), []),
    onError = useCallback(
      (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
      [],
    );
  const navigate = (path: string) => {
    location.hash = path;
    setMobileMenu(false);
    setError("");
  };
  useEffect(() => {
    const listener = () => {
      setRoute(location.hash.slice(1) || "recipes");
      setSelected(null);
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", listener);
    return () => window.removeEventListener("hashchange", listener);
  }, []);
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(""), 4500);
      return () => clearTimeout(timer);
    }
  }, [toast]);
  useEffect(() => {
    void api<Settings>("/settings").then(setSettings).catch(onError);
  }, [refresh]);
  useEffect(() => {
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () =>
      (document.documentElement.dataset.theme =
        settings.theme === "system"
          ? query.matches
            ? "dark"
            : "light"
          : settings.theme);
    apply();
    query.addEventListener("change", apply);
    return () => query.removeEventListener("change", apply);
  }, [settings.theme]);
  useEffect(() => {
    let active = true;
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        if (route.startsWith("recipe/")) {
          const r = await api<Recipe>("/recipes/" + route.split("/")[1]);
          if (active) setSelected(r);
        } else if (route === "recipes" || route === "favourites") {
          const params = new URLSearchParams({
            ...filters,
            q: search,
            ...(route === "favourites" ? { favourite: "true" } : {}),
          });
          const rows = await api<Recipe[]>("/recipes?" + params);
          if (active) setRecipes(rows);
        }
      } catch (e) {
        if (active) onError(e);
      } finally {
        if (active) setLoading(false);
      }
    }, 200);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [route, search, filters, refresh]);
  const favourite = async (r: Recipe) => {
    try {
      const next = await api<Recipe>(`/recipes/${r.id}/personal`, "PATCH", {
        favourite: !r.personal.favourite,
      });
      setRecipes((rows) => rows.map((v) => (v.id === r.id ? next : v)));
      setRefresh((n) => n + 1);
    } catch (e) {
      onError(e);
    }
  };
  const saved = (r: Recipe) => {
    setForm(null);
    setSelected(r);
    setRefresh((n) => n + 1);
    navigate(`recipe/${r.id}`);
    notify("Recipe saved");
  };
  const cards = (rows: Recipe[]) => (
    <div className="recipe-grid">
      {rows.map((r) => (
        <RecipeCard
          key={r.id}
          recipe={r}
          onOpen={(id) => navigate(`recipe/${id}`)}
          onFavourite={(r) => void favourite(r)}
        />
      ))}
    </div>
  );
  const library = route === "recipes" || route === "favourites";
  return (
    <div className="app-shell">
      <aside className={"sidebar " + (mobileMenu ? "mobile-open" : "")}>
        <a href="#recipes" className="brand">
          <span className="brand-icon">
            <Leaf size={24} />
          </span>
          <span>
            MyCookBook<small>A little inspiration. Every day.</small>
          </span>
        </a>
        <div className="nav-caption">YOUR KITCHEN</div>
        <nav aria-label="Main navigation">
          {navigation.map(([id, label, Icon]) => (
            <a
              key={id}
              href={"#" + id}
              onClick={() => setMobileMenu(false)}
              className={
                route === id ||
                (id === "recipes" && route.startsWith("recipe/"))
                  ? "active"
                  : ""
              }
            >
              <Icon size={20} />
              {label}
            </a>
          ))}
        </nav>
        <div className="sidebar-note">
          <ChefHat size={27} />
          <h4>Good food starts here.</h4>
          <p>
            Your recipes, your rhythm.
            <br />
            Made for everyday cooking.
          </p>
          <span>
            <span className="local-dot" /> Stored on your device’s server
          </span>
        </div>
        <div className="sidebar-footer">
          MyCookBook <span>LOCAL & PERSONAL</span>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="mobile-brand">
            <button
              className="icon-button"
              aria-label="Toggle navigation"
              aria-expanded={mobileMenu}
              onClick={() => setMobileMenu(!mobileMenu)}
            >
              <Menu />
            </button>
            <span>MyCookBook</span>
          </div>
          <span className="topbar-label">Your personal kitchen companion</span>
          <div className="topbar-actions">
            <button className="text-button" onClick={() => setImporting(true)}>
              <Upload size={17} /> <span>Import recipe</span>
            </button>
            <button
              className="button small"
              onClick={() => setForm(emptyRecipe(settings.default_servings))}
            >
              <Plus size={17} /> Add recipe
            </button>
          </div>
        </header>
        <div className="page-content">
          {error && (
            <div className="error-banner" role="alert">
              <div>
                <strong>Something needs your attention</strong>
                <p>{error}</p>
              </div>
              <button
                className="icon-button"
                aria-label="Dismiss error"
                onClick={() => setError("")}
              >
                <X size={18} />
              </button>
            </div>
          )}
          {library && (
            <>
              <div className="page-heading">
                <div className="eyebrow">A collection to come home to</div>
                <h1>
                  {route === "favourites"
                    ? "Your tried-and-loved favourites"
                    : "Something delicious starts here."}
                </h1>
                <p>
                  {route === "favourites"
                    ? "The recipes you always come back to."
                    : "Gather your favourites, discover a new dish, and make every meal your own."}
                </p>
              </div>
              <div className="library-toolbar">
                <div className="search-box">
                  <Search size={19} />
                  <input
                    aria-label="Search recipes"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search recipes, ingredients, cuisines…"
                  />
                </div>
                <button
                  className={
                    "button secondary " + (showFilters ? "selected" : "")
                  }
                  onClick={() => setShowFilters(!showFilters)}
                  aria-expanded={showFilters}
                >
                  <SlidersHorizontal size={17} /> Filters
                </button>
                <label className="sort-label">
                  <span className="sr-only">Sort recipes</span>
                  <select
                    value={filters.sort}
                    onChange={(e) =>
                      setFilters({ ...filters, sort: e.target.value })
                    }
                  >
                    <option value="recent">Recently added</option>
                    <option value="alphabetical">A to Z</option>
                    <option value="cooked">Recently cooked</option>
                    <option value="rating">Highest rated</option>
                    <option value="quickest">Quickest first</option>
                    <option value="frequent">Most cooked</option>
                  </select>
                </label>
              </div>
              {showFilters && (
                <section className="filter-panel">
                  <label>
                    Main ingredient
                    <input
                      value={filters.ingredient || ""}
                      onChange={(e) =>
                        setFilters({ ...filters, ingredient: e.target.value })
                      }
                      placeholder="Chicken, chickpeas…"
                    />
                  </label>
                  <label>
                    Cuisine
                    <input
                      value={filters.cuisine || ""}
                      onChange={(e) =>
                        setFilters({ ...filters, cuisine: e.target.value })
                      }
                    />
                  </label>
                  <label>
                    Maximum time (min)
                    <input
                      type="number"
                      min="0"
                      value={filters.max_time || ""}
                      onChange={(e) =>
                        setFilters({ ...filters, max_time: e.target.value })
                      }
                    />
                  </label>
                  <label>
                    Difficulty
                    <select
                      value={filters.difficulty || ""}
                      onChange={(e) =>
                        setFilters({ ...filters, difficulty: e.target.value })
                      }
                    >
                      <option value="">Any difficulty</option>
                      {["Easy", "Medium", "Hard"].map((v) => (
                        <option key={v}>{v}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Equipment
                    <select
                      value={filters.equipment || ""}
                      onChange={(e) =>
                        setFilters({ ...filters, equipment: e.target.value })
                      }
                    >
                      <option value="">Any equipment</option>
                      {equipmentOptions.map((v) => (
                        <option key={v}>{v}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Feedback
                    <select
                      value={filters.feedback || ""}
                      onChange={(e) =>
                        setFilters({ ...filters, feedback: e.target.value })
                      }
                    >
                      <option value="">Any feedback</option>
                      <option value="positive">Liked</option>
                      <option value="negative">Disliked</option>
                      <option value="neutral">Neutral</option>
                    </select>
                  </label>
                  <label>
                    Cooking history
                    <select
                      value={filters.cooked || ""}
                      onChange={(e) =>
                        setFilters({ ...filters, cooked: e.target.value })
                      }
                    >
                      <option value="">All recipes</option>
                      <option value="true">Previously cooked</option>
                      <option value="false">Never cooked</option>
                    </select>
                  </label>
                  <label className="inline-check">
                    <input
                      type="checkbox"
                      checked={filters.favourite === "true"}
                      onChange={(e) =>
                        setFilters({
                          ...filters,
                          favourite: e.target.checked ? "true" : "",
                        })
                      }
                    />
                    Favourites only
                  </label>
                  <button
                    className="text-button"
                    onClick={() => {
                      setFilters({ sort: "recent" });
                      setSearch("");
                    }}
                  >
                    Clear filters
                  </button>
                </section>
              )}
              <div className="section-heading library-heading">
                <h2>
                  {route === "favourites"
                    ? "Favourites"
                    : "Your recipe collection"}{" "}
                  <span className="count">{recipes.length}</span>
                </h2>
                <span className="muted">
                  A little inspiration for your next meal
                </span>
              </div>
              {loading ? (
                <Loading />
              ) : recipes.length ? (
                cards(recipes)
              ) : (
                <Empty
                  title={
                    search || Object.keys(filters).length > 1
                      ? "No recipes match these filters"
                      : "Your next favourite is waiting"
                  }
                  text="Add your own recipe, import a collection, or try the clearly labelled sample recipes."
                >
                  <button
                    className="button"
                    onClick={() =>
                      setForm(emptyRecipe(settings.default_servings))
                    }
                  >
                    <Plus size={17} /> Add your first recipe
                  </button>
                  <button
                    className="button secondary"
                    onClick={async () => {
                      try {
                        await api("/demo", "POST");
                        setRefresh((n) => n + 1);
                        notify("Six demo recipes loaded");
                      } catch (e) {
                        onError(e);
                      }
                    }}
                  >
                    Try demo recipes
                  </button>
                </Empty>
              )}
            </>
          )}
          {route.startsWith("recipe/") &&
            (loading ? (
              <Loading />
            ) : selected ? (
              <RecipeDetail
                key={selected.id}
                recipe={selected}
                onUpdate={setSelected}
                onEdit={() => setForm(selected)}
                onBack={() => {
                  navigate("recipes");
                  setRefresh((n) => n + 1);
                }}
                notify={notify}
                onError={onError}
              />
            ) : (
              <Empty
                title="Recipe unavailable"
                text="Return to your collection to choose a recipe."
              >
                <button className="button" onClick={() => navigate("recipes")}>
                  Open recipes
                </button>
              </Empty>
            ))}
          {route === "discover" && (
            <Discovery cards={cards} onError={onError} />
          )}
          {route === "shopping" && (
            <ShoppingPage
              onError={onError}
              notify={notify}
              onPreferencesChanged={() => setRefresh((n) => n + 1)}
            />
          )}
          {route === "history" && (
            <HistoryPage
              onOpen={(id) => navigate(`recipe/${id}`)}
              onError={onError}
            />
          )}
          {route === "settings" && (
            <SettingsPage
              settings={settings}
              onSettings={setSettings}
              onError={onError}
              notify={notify}
              onImport={() => setImporting(true)}
              onRefresh={() => setRefresh((n) => n + 1)}
            />
          )}
          {!navigation.some(([id]) => id === route) &&
            !route.startsWith("recipe/") && (
              <Empty
                title="Page not found"
                text="Your recipe collection is a good place to start."
              >
                <a href="#recipes" className="button">
                  Open recipes
                </a>
              </Empty>
            )}
        </div>
        <footer className="page-footer">
          <Leaf size={15} /> A place for the recipes you love.
        </footer>
      </main>
      <nav className="bottom-nav" aria-label="Mobile navigation">
        {navigation.slice(0, 5).map(([id, label, Icon]) => (
          <a key={id} href={"#" + id} className={route === id ? "active" : ""}>
            <Icon size={21} />
            <span>
              {id === "discover"
                ? "Discover"
                : id === "history"
                  ? "History"
                  : id === "shopping"
                    ? "Shopping"
                    : label}
            </span>
          </a>
        ))}
      </nav>
      {form && (
        <Modal
          title={
            (form as Recipe).id
              ? "Edit recipe"
              : "A new recipe for your collection"
          }
          onClose={() => setForm(null)}
        >
          <RecipeForm
            initial={form}
            onSave={saved}
            onCancel={() => setForm(null)}
            onError={onError}
          />
        </Modal>
      )}
      {importing && (
        <Modal
          title="Bring your recipes home"
          onClose={() => setImporting(false)}
        >
          <ImportPanel
            llm={!!settings.llm_configured}
            onRecipe={(r) => {
              setImporting(false);
              setForm(r);
            }}
            onDone={() => {
              setImporting(false);
              setRefresh((n) => n + 1);
              notify("Import complete");
            }}
            onError={onError}
          />
        </Modal>
      )}
      {toast && (
        <div className="toast" role="status">
          <Check size={18} />
          {toast}
          <button
            aria-label="Dismiss notification"
            onClick={() => setToast("")}
          >
            <X size={16} />
          </button>
        </div>
      )}
      {error && (form || importing) && (
        <div className="toast error-toast" role="alert">
          {error}
          <button aria-label="Dismiss error" onClick={() => setError("")}>
            <X size={18} />
          </button>
        </div>
      )}
    </div>
  );
}

function Loading() {
  return (
    <div className="loading" role="status">
      <div className="spinner" /> Getting your kitchen ready…
    </div>
  );
}
function Empty({
  title,
  text,
  children,
}: {
  title: string;
  text: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <BookOpen size={34} />
      </span>
      <h2>{title}</h2>
      <p>{text}</p>
      <div className="row">{children}</div>
    </div>
  );
}

function Discovery({
  cards,
  onError,
}: {
  cards: (r: Recipe[]) => React.ReactNode;
  onError: (e: unknown) => void;
}) {
  const [mode, setMode] = useState("suggest"),
    [ingredients, setIngredients] = useState(""),
    [filters, setFilters] = useState<Record<string, string>>({
      exclude_disliked: "true",
      include_cooked: "true",
      prioritise_favourites: "true",
      not_recent: "true",
    }),
    [rows, setRows] = useState<Recipe[]>([]),
    [busy, setBusy] = useState(false),
    [searched, setSearched] = useState(false);
  const search = async (surprise = false) => {
    setBusy(true);
    try {
      setRows(
        mode === "pantry"
          ? await api<Recipe[]>("/pantry", "POST", {
              ingredients: ingredients
                .split(",")
                .map((v) => v.trim())
                .filter(Boolean),
            })
          : await api<Recipe[]>(
              "/recommendations?" +
                new URLSearchParams({ ...filters, surprise: String(surprise) }),
            ),
      );
      setSearched(true);
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <div className="page-heading">
        <div className="eyebrow">A little kitchen inspiration</div>
        <h1>What sounds good today?</h1>
        <p>
          Find something that fits your mood, your time, and what’s in the
          fridge.
        </p>
      </div>
      <div className="segmented">
        <button
          className={mode === "suggest" ? "active" : ""}
          onClick={() => {
            setMode("suggest");
            setSearched(false);
          }}
        >
          Help me choose
        </button>
        <button
          className={mode === "pantry" ? "active" : ""}
          onClick={() => {
            setMode("pantry");
            setSearched(false);
          }}
        >
          What can I make?
        </button>
      </div>
      <section className="panel discovery-form">
        {mode === "pantry" ? (
          <label>
            Ingredients you have (comma separated)
            <textarea
              rows={3}
              value={ingredients}
              onChange={(e) => setIngredients(e.target.value)}
              placeholder="Chicken, lemon, pasta, garlic…"
            />
          </label>
        ) : (
          <>
            <div className="filter-panel">
              <label>
                Time available (minutes)
                <input
                  type="number"
                  min="0"
                  value={filters.max_time || ""}
                  onChange={(e) =>
                    setFilters({ ...filters, max_time: e.target.value })
                  }
                  placeholder="Any time"
                />
              </label>
              <label>
                Main ingredient
                <input
                  value={filters.ingredient || ""}
                  onChange={(e) =>
                    setFilters({ ...filters, ingredient: e.target.value })
                  }
                />
              </label>
              <label>
                Cuisine
                <input
                  value={filters.cuisine || ""}
                  onChange={(e) =>
                    setFilters({ ...filters, cuisine: e.target.value })
                  }
                />
              </label>
              <label>
                Difficulty
                <select
                  value={filters.difficulty || ""}
                  onChange={(e) =>
                    setFilters({ ...filters, difficulty: e.target.value })
                  }
                >
                  <option value="">Any</option>
                  {["Easy", "Medium", "Hard"].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="check-grid">
              {[
                ["include_cooked", "Include previously cooked"],
                ["exclude_disliked", "Exclude disliked recipes"],
                ["prioritise_favourites", "Prioritise favourites"],
                ["not_recent", "Prioritise recipes not cooked recently"],
              ].map(([key, label]) => (
                <label key={key}>
                  <input
                    type="checkbox"
                    checked={filters[key] === "true"}
                    onChange={(e) =>
                      setFilters({
                        ...filters,
                        [key]: String(e.target.checked),
                      })
                    }
                  />
                  {label}
                </label>
              ))}
            </div>
            <p className="muted small-text">
              Suggestions respect your equipment and exclusions in Settings.
              Ratings, favourites and time since last cooked determine the
              order. Dietary filters use ingredient keywords; review the full
              recipe for suitability.
            </p>
          </>
        )}
        <div className="row">
          <button
            className="button"
            disabled={busy}
            onClick={() => void search()}
          >
            <Sparkles size={17} />
            {busy
              ? "Finding recipes…"
              : mode === "pantry"
                ? "Find matching recipes"
                : "Find my next meal"}
          </button>
          {mode === "suggest" && (
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => void search(true)}
            >
              Surprise me
            </button>
          )}
        </div>
      </section>
      {searched &&
        (rows.length ? (
          cards(rows)
        ) : (
          <Empty
            title="No matches just yet"
            text="Try fewer filters, update your available equipment, or add a few more recipes."
          />
        ))}
    </>
  );
}

function ShoppingPage({
  onError,
  notify,
  onPreferencesChanged,
}: {
  onError: (e: unknown) => void;
  notify: (m: string) => void;
  onPreferencesChanged: () => void;
}) {
  const [rows, setRows] = useState<Shopping[]>([]),
    [name, setName] = useState(""),
    [quantity, setQuantity] = useState(""),
    [unit, setUnit] = useState(""),
    [busy, setBusy] = useState(true);
  const load = async () => {
    try {
      setRows(await api<Shopping[]>("/shopping"));
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    void load();
  }, []);
  const action = async (path: string, method: string, data?: unknown) => {
    try {
      await api(path, method, data);
      await load();
    } catch (e) {
      onError(e);
    }
  };
  return (
    <>
      <div className="page-heading">
        <div className="eyebrow">From your kitchen to your basket</div>
        <h1>A little list. A better shop.</h1>
        <p>
          Add scaled ingredients from any recipe, or jot down the extras you
          need.
        </p>
        <p className="muted small-text">
          Use “Always have” on an item to remember a cupboard staple and skip it
          next time. Manage your list in{" "}
          <a className="text-button" href="#settings">
            Settings
          </a>
          . You can still add staples manually when they run out.
        </p>
      </div>
      <section className="panel">
        <form
          className="shopping-add"
          onSubmit={async (e) => {
            e.preventDefault();
            await action("/shopping", "POST", {
              name,
              quantity: quantity === "" ? null : Number(quantity),
              unit,
            });
            setName("");
            setQuantity("");
            setUnit("");
          }}
        >
          <label>
            Item
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Add something to your list"
            />
          </label>
          <label>
            Quantity
            <input
              type="number"
              min="0"
              step="any"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
          </label>
          <label>
            Unit
            <input
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              placeholder="g, ml…"
            />
          </label>
          <button className="button">
            <Plus size={18} />
            Add
          </button>
        </form>
      </section>
      <div className="section-heading">
        <h2>
          Your shopping list{" "}
          <span className="count">{rows.filter((i) => !i.checked).length}</span>
        </h2>
        <button
          className="text-button"
          disabled={!rows.some((i) => i.checked)}
          onClick={async () => {
            await action("/shopping/completed", "DELETE");
            notify("Completed items cleared");
          }}
        >
          Clear completed
        </button>
      </div>
      {busy ? (
        <Loading />
      ) : rows.length ? (
        <section className="panel shopping-list">
          {[...new Set(rows.map((i) => i.category))].map((category) => (
            <div key={category}>
              <h3>{category}</h3>
              {rows
                .filter((i) => i.category === category)
                .map((i) => (
                  <div className="shopping-row" key={i.id}>
                    <label className={i.checked ? "checked" : ""}>
                      <input
                        type="checkbox"
                        checked={i.checked}
                        onChange={(e) =>
                          void action(`/shopping/${i.id}`, "PATCH", {
                            checked: e.target.checked,
                          })
                        }
                      />
                      <span>
                        <strong>
                          {formatQuantity(i.quantity, 1, 1)} {i.unit}
                        </strong>{" "}
                        {i.name}
                        {i.preparation ? ", " + i.preparation : ""}
                      </span>
                    </label>
                    {!i.checked && (
                      <button
                        className="text-button staple-button"
                        aria-label={`Always have ${i.name}`}
                        onClick={async () => {
                          try {
                            setRows(
                              await api<Shopping[]>(
                                `/shopping/${i.id}/staple`,
                                "POST",
                              ),
                            );
                            onPreferencesChanged();
                            notify(`${i.name} saved as a cupboard staple`);
                          } catch (e) {
                            onError(e);
                          }
                        }}
                      >
                        Always have
                      </button>
                    )}
                    <button
                      className="icon-button danger"
                      aria-label={`Remove ${i.name}`}
                      onClick={() => void action(`/shopping/${i.id}`, "DELETE")}
                    >
                      <Trash2 size={17} />
                    </button>
                  </div>
                ))}
            </div>
          ))}
        </section>
      ) : (
        <Empty
          title="Your basket starts here"
          text="Open a recipe and add its ingredients, or add an item above."
        />
      )}
    </>
  );
}

function HistoryPage({
  onOpen,
  onError,
}: {
  onOpen: (id: number) => void;
  onError: (e: unknown) => void;
}) {
  const [rows, setRows] = useState<Session[]>([]),
    [busy, setBusy] = useState(true);
  useEffect(() => {
    void api<Session[]>("/history")
      .then(setRows)
      .catch(onError)
      .finally(() => setBusy(false));
  }, []);
  const frequent = Object.values(
    rows.reduce<Record<number, { id: number; title: string; count: number }>>(
      (a, h) => {
        a[h.recipe_id] ??= { id: h.recipe_id, title: h.title || "", count: 0 };
        a[h.recipe_id].count++;
        return a;
      },
      {},
    ),
  ).sort((a, b) => b.count - a.count);
  return (
    <>
      <div className="page-heading">
        <div className="eyebrow">Made, enjoyed, remembered</div>
        <h1>Stories from your kitchen.</h1>
        <p>Your recent meals and the favourites you keep coming back to.</p>
      </div>
      {busy ? (
        <Loading />
      ) : rows.length ? (
        <>
          <div className="stats-row">
            <div className="panel">
              <strong>{rows.length}</strong>
              <span>Meals recorded</span>
            </div>
            <div className="panel">
              <strong>{frequent.length}</strong>
              <span>Different recipes</span>
            </div>
          </div>
          <section className="panel">
            <h2>Most often on the menu</h2>
            {frequent.slice(0, 5).map((r) => (
              <div key={r.id} className="history-row">
                <button className="title-link" onClick={() => onOpen(r.id)}>
                  {r.title}
                </button>
                <span>{r.count} meals</span>
              </div>
            ))}
          </section>
          <section className="panel">
            <h2>Recent meals</h2>
            {rows.map((h) => (
              <div className="history-row" key={h.id}>
                <div>
                  <button
                    className="title-link"
                    onClick={() => onOpen(h.recipe_id)}
                  >
                    <strong>{h.title}</strong>
                  </button>
                  <p>
                    {new Date(h.cooked_at).toLocaleDateString()} · {h.servings}{" "}
                    portions{h.rating ? ` · ${h.rating}/5 stars` : ""}
                  </p>
                  {h.notes && <p>{h.notes}</p>}
                </div>
              </div>
            ))}
          </section>
        </>
      ) : (
        <Empty
          title="The first meal is a good place to start"
          text="Finish cooking mode or use Record a meal on a recipe to start your history."
        />
      )}
    </>
  );
}

function SettingsPage({
  settings,
  onSettings,
  onError,
  notify,
  onImport,
  onRefresh,
}: {
  settings: Settings;
  onSettings: (s: Settings) => void;
  onError: (e: unknown) => void;
  notify: (m: string) => void;
  onImport: () => void;
  onRefresh: () => void;
}) {
  const [form, setForm] = useState(settings),
    [busy, setBusy] = useState(false);
  useEffect(() => setForm(settings), [settings]);
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { llm_configured, ...data } = form;
      onSettings(await api<Settings>("/settings", "PUT", data));
      notify("Kitchen preferences saved");
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <div className="page-heading">
        <div className="eyebrow">Make yourself at home</div>
        <h1>Your kitchen, your way.</h1>
        <p>A few preferences to make everyday cooking feel easier.</p>
      </div>
      <form className="panel settings-form" onSubmit={save}>
        <h2>Everyday preferences</h2>
        <div className="form-grid">
          <label>
            Default portions for new recipes
            <input
              type="number"
              min="0.1"
              max="1000"
              step="any"
              value={form.default_servings}
              onChange={(e) =>
                setForm({ ...form, default_servings: Number(e.target.value) })
              }
            />
          </label>
          <label>
            Appearance
            <select
              value={form.theme}
              onChange={(e) =>
                setForm({ ...form, theme: e.target.value as Settings["theme"] })
              }
            >
              <option value="system">Follow device</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </label>
        </div>
        <fieldset>
          <legend>Equipment available</legend>
          <div className="check-grid">
            {equipmentOptions.map((v) => (
              <label key={v}>
                <input
                  type="checkbox"
                  checked={form.equipment.includes(v)}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      equipment: e.target.checked
                        ? [...form.equipment, v]
                        : form.equipment.filter((x) => x !== v),
                    })
                  }
                />
                {v}
              </label>
            ))}
          </div>
          <p className="muted small-text">
            An empty selection allows all equipment in suggestions.
          </p>
        </fieldset>
        <label>
          Ingredients to exclude from suggestions (comma separated)
          <input
            value={form.ingredient_exclusions.join(", ")}
            onChange={(e) =>
              setForm({
                ...form,
                ingredient_exclusions: e.target.value
                  .split(",")
                  .map((v) => v.trim()),
              })
            }
            placeholder="Mushrooms, prawns…"
          />
        </label>
        <fieldset>
          <legend>Cupboard staples — ingredients you always have</legend>
          <p className="muted small-text">
            Recipe shopping additions skip these ingredients. Use the ingredient
            names shown in your recipes. Salt and pepper are included to get you
            started; add your usual sauces, oils and seasonings here.
          </p>
          <label>
            Always have (comma separated)
            <textarea
              rows={3}
              value={form.shopping_staples.join(", ")}
              onChange={(e) =>
                setForm({
                  ...form,
                  shopping_staples: e.target.value
                    .split(",")
                    .map((v) => v.trim()),
                })
              }
              placeholder="Salt, ground black pepper, light soy sauce, paprika…"
            />
          </label>
          <button
            type="button"
            className="text-button"
            onClick={() =>
              setForm({
                ...form,
                shopping_staples: [
                  ...new Set([
                    ...form.shopping_staples.filter(Boolean),
                    "light soy sauce",
                    "dark soy sauce",
                    "oyster sauce",
                    "sriracha",
                    "olive oil",
                    "neutral oil",
                    "sesame oil",
                    "paprika",
                    "smoked paprika",
                    "garlic powder",
                    "onion powder",
                    "Cajun seasoning",
                  ]),
                ],
              })
            }
          >
            Add common sauces, oils & seasonings
          </button>
          <p className="muted small-text">
            Remove a name to include it in future shopping additions, or tick
            “Include cupboard staples this time” on a recipe when restocking.
            Save preferences to apply changes.
          </p>
        </fieldset>
        <label>
          Dietary preferences (comma separated)
          <input
            value={form.dietary_exclusions.join(", ")}
            onChange={(e) =>
              setForm({
                ...form,
                dietary_exclusions: e.target.value
                  .split(",")
                  .map((v) => v.trim()),
              })
            }
            placeholder="Vegetarian, vegan, dairy-free, gluten-free"
          />
        </label>
        <button className="button" disabled={busy}>
          {busy ? "Saving…" : "Save preferences"}
        </button>
      </form>
      <section className="panel">
        <h2>Recipe data & backups</h2>
        <p>
          JSON exports are portable. Personal backups include feedback, history,
          preferences and your shopping list. Photos are included by the archive
          backup script described in the README.
        </p>
        <div className="row">
          <button className="button secondary" onClick={onImport}>
            <Upload size={17} /> Import / restore JSON
          </button>
          <a className="button secondary" href="/api/export" download>
            <Download size={17} /> Export recipes
          </a>
          <a
            className="button secondary"
            href="/api/export?backup=true"
            download
          >
            <Download size={17} /> Personal JSON backup
          </a>
        </div>
      </section>
      <section className="panel">
        <h2>Optional recipe extraction</h2>
        <p>
          <strong>
            {settings.llm_configured ? "Configured" : "Not configured"}
          </strong>{" "}
          · The local text parser is always available.
        </p>
        <p className="muted">
          An optional OpenAI-compatible endpoint can be configured by the server
          administrator with LLM_API_URL, LLM_MODEL and LLM_API_KEY. Credentials
          stay on the server.
        </p>
      </section>
      <section className="panel">
        <h2>Explore with sample recipes</h2>
        <p>
          Six demonstration recipes, written for this app. These are not
          recovered personal recipes. Removing demos also removes their cooking
          history.
        </p>
        <div className="row">
          <button
            className="button secondary"
            onClick={async () => {
              try {
                const r = await api<{ message: string }>("/demo", "POST");
                notify(r.message);
                onRefresh();
              } catch (e) {
                onError(e);
              }
            }}
          >
            Load demo recipes
          </button>
          <button
            className="text-button danger"
            onClick={async () => {
              if (
                !window.confirm(
                  "Remove all bundled demo recipes and their cooking history?",
                )
              )
                return;
              try {
                const r = await api<{ message: string }>("/demo", "DELETE");
                notify(r.message);
                onRefresh();
              } catch (e) {
                onError(e);
              }
            }}
          >
            Remove demo recipes
          </button>
        </div>
      </section>
    </>
  );
}
