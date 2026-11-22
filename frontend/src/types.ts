export type Ingredient = {
  name: string;
  quantity: number | null;
  unit: string;
  preparation: string;
  optional: boolean;
  group: string;
  category: string;
};
export type Step = { text: string; timer_seconds: number | null };
export type Personal = {
  favourite: boolean;
  feedback: "positive" | "negative" | "neutral";
  rating: number | null;
  notes: string;
  would_cook_again: boolean | null;
  selected_servings: number | null;
};
export type Session = {
  id: number;
  recipe_id: number;
  cooked_at: string;
  servings: number;
  rating: number | null;
  notes: string;
  title?: string;
};
export type RecipeContent = {
  title: string;
  description: string;
  servings: number;
  prep_time: number;
  cook_time: number;
  total_time: number | null;
  difficulty: "Easy" | "Medium" | "Hard";
  cuisine: string;
  category: string;
  tags: string[];
  ingredients: Ingredient[];
  instructions: Step[];
  equipment: string[];
  equipment_alternatives: string[];
  image_path: string;
  source: string;
  demo: boolean;
};
export type Recipe = RecipeContent & {
  id: number;
  personal: Personal;
  created_at: string;
  updated_at: string;
  times_cooked: number;
  last_cooked: string | null;
  history?: Session[];
  reason?: string;
  matched?: string[];
  missing?: string[];
  coverage?: number;
};
export type Shopping = {
  id: number;
  name: string;
  quantity: number | null;
  unit: string;
  preparation: string;
  category: string;
  checked: boolean;
};
export type Settings = {
  default_servings: number;
  theme: "light" | "dark" | "system";
  equipment: string[];
  dietary_exclusions: string[];
  ingredient_exclusions: string[];
  shopping_staples: string[];
  llm_configured?: boolean;
};
export const equipmentOptions = [
  "Hob",
  "Frying pan",
  "Saucepan/pot",
  "Air fryer",
  "Oven",
  "Microwave",
  "Other",
];
export const emptyIngredient = (): Ingredient => ({
  name: "",
  quantity: null,
  unit: "",
  preparation: "",
  optional: false,
  group: "",
  category: "Other",
});
export const emptyRecipe = (servings = 2): RecipeContent => ({
  title: "",
  description: "",
  servings,
  prep_time: 0,
  cook_time: 0,
  total_time: null,
  difficulty: "Easy",
  cuisine: "",
  category: "Dinner",
  tags: [],
  ingredients: [emptyIngredient()],
  instructions: [{ text: "", timer_seconds: null }],
  equipment: [],
  equipment_alternatives: [],
  image_path: "",
  source: "",
  demo: false,
});
export function contentOnly(r: RecipeContent): RecipeContent {
  const keys = Object.keys(emptyRecipe()) as (keyof RecipeContent)[];
  return Object.fromEntries(keys.map((k) => [k, r[k]])) as RecipeContent;
}
