import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { formatQuantity } from "./api";
import { Portions, Stars } from "./components";
import RecipeDetail from "./RecipeDetail";
import { Recipe, emptyRecipe } from "./types";
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
describe("portion scaling", () => {
  it("scales from original quantities and formats fractions without changing originals", () => {
    const source = { quantity: 300 };
    expect(formatQuantity(source.quantity, 3, 2)).toBe("450");
    expect(formatQuantity(0.5, 3, 2)).toBe("¾");
    expect(formatQuantity(null, 3, 2)).toBe("");
    expect(formatQuantity(1 / 3, 2, 2)).toBe("⅓");
    expect(source.quantity).toBe(300);
  });
  it("updates accessible portion controls and enforces limits", async () => {
    const user = userEvent.setup();
    function Harness() {
      const [value, setValue] = useState(2);
      return <Portions value={value} onChange={setValue} />;
    }
    render(<Harness />);
    await user.click(screen.getByRole("button", { name: "More portions" }));
    expect(screen.getByText("3")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Fewer portions" }));
    await user.click(screen.getByRole("button", { name: "Fewer portions" }));
    expect(
      screen.getByRole("button", { name: "Fewer portions" }),
    ).toBeDisabled();
  });
  it("allows clearing star feedback", async () => {
    const onChange = vi.fn();
    render(<Stars value={4} onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "Rate 4 stars" }));
    expect(onChange).toHaveBeenCalledWith(null);
  });
  it("scales displayed ingredients, preserves method and posts selected servings", async () => {
    const recipe: Recipe = {
      ...emptyRecipe(),
      id: 1,
      title: "Dinner",
      ingredients: [
        {
          name: "chicken",
          quantity: 300,
          unit: "g",
          preparation: "",
          optional: false,
          group: "",
          category: "Other",
        },
      ],
      instructions: [{ text: "Cook for 20 minutes.", timer_seconds: null }],
      personal: {
        favourite: false,
        feedback: "neutral",
        rating: null,
        notes: "",
        would_cook_again: null,
        selected_servings: null,
      },
      created_at: "",
      updated_at: "",
      times_cooked: 0,
      last_cooked: null,
      history: [],
    };
    const fetch = vi
      .fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => recipe });
    vi.stubGlobal("fetch", fetch);
    render(
      <RecipeDetail
        recipe={recipe}
        onUpdate={() => {}}
        onEdit={() => {}}
        onBack={() => {}}
        notify={() => {}}
        onError={() => {}}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "More portions" }));
    expect(screen.getByText("450 g")).toBeInTheDocument();
    expect(screen.getByText("Cook for 20 minutes.")).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Add to shopping list" }),
    );
    expect(fetch).toHaveBeenCalledWith(
      "/api/recipes/1/shopping",
      expect.objectContaining({
        body: JSON.stringify({
          servings: 3,
          include_optional: false,
          include_staples: false,
          exclude_ingredient_indices: [],
        }),
      }),
    );
    expect(recipe.ingredients[0].quantity).toBe(300);
    const chicken = screen.getByRole("checkbox", { name: /chicken/ });
    await user.click(chicken);
    await user.click(
      screen.getByRole("button", { name: "Add to shopping list" }),
    );
    expect(fetch).toHaveBeenLastCalledWith(
      "/api/recipes/1/shopping",
      expect.objectContaining({
        body: JSON.stringify({
          servings: 3,
          include_optional: false,
          include_staples: false,
          exclude_ingredient_indices: [0],
        }),
      }),
    );
    await user.click(chicken);
    await user.click(
      screen.getByRole("button", { name: "Add to shopping list" }),
    );
    expect(
      JSON.parse(fetch.mock.lastCall![1].body).exclude_ingredient_indices,
    ).toEqual([]);
  });
});
