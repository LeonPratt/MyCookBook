import { useState, useEffect, useRef } from "react";
import {
  Heart,
  Clock3,
  Users,
  Leaf,
  ChefHat,
  Minus,
  Plus,
  X,
  Star,
} from "lucide-react";
import { Recipe } from "./types";

export function Portions({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="portions" aria-label="Portion selector">
      <button
        aria-label="Fewer portions"
        disabled={value <= 1}
        onClick={() => onChange(Math.max(1, value - 1))}
      >
        <Minus size={16} />
      </button>
      <span>
        <strong>{value}</strong> portions
      </span>
      <button
        aria-label="More portions"
        disabled={value >= 1000}
        onClick={() => onChange(Math.min(1000, value + 1))}
      >
        <Plus size={16} />
      </button>
    </div>
  );
}
export function Stars({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (n: number | null) => void;
}) {
  return (
    <div className="stars" aria-label="Recipe rating">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          aria-label={`Rate ${n} stars`}
          aria-pressed={value === n}
          onClick={() => onChange(value === n ? null : n)}
        >
          <Star size={21} fill={(value || 0) >= n ? "currentColor" : "none"} />
        </button>
      ))}
    </div>
  );
}
export function FoodArt({
  recipe,
  large = false,
}: {
  recipe: Recipe;
  large?: boolean;
}) {
  return recipe.image_path ? (
    <img
      className={`food-art ${large ? "large" : ""}`}
      src={recipe.image_path}
      alt={recipe.title}
    />
  ) : (
    <div
      className={`food-art illustrated art-${recipe.id % 6} ${large ? "large" : ""}`}
      aria-label="Recipe illustration"
    >
      <div className="plate">
        <div className="food-shape shape-1" />
        <div className="food-shape shape-2" />
        <div className="food-shape shape-3" />
        <div className="garnish">
          <Leaf size={large ? 42 : 30} />
        </div>
      </div>
      <span className="art-caption">{recipe.category || "Made at home"}</span>
    </div>
  );
}
export function RecipeCard({
  recipe: r,
  onOpen,
  onFavourite,
}: {
  recipe: Recipe;
  onOpen: (id: number) => void;
  onFavourite: (r: Recipe) => void;
}) {
  return (
    <article className="recipe-card">
      <div className="card-image">
        <button
          className="image-link"
          onClick={() => onOpen(r.id)}
          aria-label={`Open ${r.title}`}
        >
          <FoodArt recipe={r} />
        </button>
        <button
          className={"heart " + (r.personal.favourite ? "active" : "")}
          onClick={() => onFavourite(r)}
          aria-label={
            r.personal.favourite ? "Remove favourite" : "Add favourite"
          }
          aria-pressed={r.personal.favourite}
        >
          <Heart
            size={19}
            fill={r.personal.favourite ? "currentColor" : "none"}
          />
        </button>
        {r.personal.rating && (
          <span className="rating-badge">
            <Star size={12} fill="currentColor" /> {r.personal.rating}
          </span>
        )}
      </div>
      <div className="card-body">
        <div className="eyebrow">
          {r.cuisine || r.category || "Your recipe"}
          {r.personal.feedback === "negative"
            ? " · Disliked"
            : r.personal.feedback === "positive"
              ? " · Liked"
              : ""}
        </div>
        <button className="title-link" onClick={() => onOpen(r.id)}>
          <h3>{r.title}</h3>
        </button>
        <p>{r.description || "A recipe from your personal collection."}</p>
        <div className="recipe-meta">
          <span>
            <Clock3 size={15} />
            {r.total_time ?? r.prep_time + r.cook_time} min
          </span>
          <span>
            <Users size={15} />
            {r.servings}
          </span>
          <span>
            <ChefHat size={15} />
            {r.difficulty}
          </span>
        </div>
        <div className="tags">
          {r.tags.slice(0, 3).map((t) => (
            <span key={t}>{t}</span>
          ))}
        </div>
        {r.reason && <p className="reason">{r.reason}</p>}
        {r.coverage !== undefined && (
          <div className="pantry-match">
            <strong>{Math.round(r.coverage * 100)}% ingredients matched</strong>
            <p>Have: {r.matched?.join(", ")}</p>
            <p>
              Missing: {r.missing?.join(", ") || "Nothing — ready to cook!"}
            </p>
          </div>
        )}
      </div>
    </article>
  );
}
export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    const old = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    ref.current?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab") {
        const items = ref.current?.querySelectorAll<HTMLElement>(
          'button:not([disabled]),input,textarea,select,a[href],[tabindex="0"]',
        );
        if (items?.length) {
          const first = items[0],
            last = items[items.length - 1];
          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.body.style.overflow = old;
      document.removeEventListener("keydown", key);
      previous?.focus();
    };
  }, [onClose]);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="modal"
        tabIndex={-1}
        ref={ref}
      >
        <div className="modal-head">
          <h2>{title}</h2>
          <button
            className="icon-button"
            aria-label="Close dialog"
            onClick={onClose}
          >
            <X />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
export function Timer({ seconds }: { seconds: number }) {
  const [remaining, setRemaining] = useState(seconds),
    [running, setRunning] = useState(false);
  const end = useRef(0);
  useEffect(() => {
    if (!running) return;
    end.current = Date.now() + remaining * 1000;
    const id = window.setInterval(() => {
      const next = Math.max(0, Math.ceil((end.current - Date.now()) / 1000));
      setRemaining(next);
      if (next === 0) setRunning(false);
    }, 250);
    return () => clearInterval(id);
  }, [running]);
  return (
    <div className="timer">
      <span role="timer" aria-live={remaining === 0 ? "polite" : "off"}>
        {Math.floor(remaining / 60)}:{String(remaining % 60).padStart(2, "0")}
        {remaining === 0 ? " · Timer complete" : ""}
      </span>
      <button
        className="button small"
        onClick={() => setRunning(!running)}
        disabled={remaining === 0}
      >
        {running ? "Pause" : "Start timer"}
      </button>
      <button
        className="text-button"
        onClick={() => {
          setRunning(false);
          setRemaining(seconds);
        }}
      >
        Reset
      </button>
    </div>
  );
}
