import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import RecipeDetail from "./RecipeDetail";
import { emptyRecipe, Recipe } from "./types";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

it("remembers a shopping item as a staple and removes it from the list", async () => {
  window.location.hash = "#shopping";
  vi.stubGlobal("scrollTo", vi.fn());
  vi.stubGlobal("matchMedia", () => ({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
  const settings = {
    default_servings: 2,
    theme: "system",
    equipment: [],
    dietary_exclusions: [],
    ingredient_exclusions: [],
    shopping_staples: ["salt"],
  };
  const fetch = vi
    .fn()
    .mockImplementation(async (path: string) => ({
      ok: true,
      status: 200,
      json: async () =>
        path === "/api/settings"
          ? settings
          : path.endsWith("/staple")
            ? []
            : [
                {
                  id: 1,
                  name: "light soy sauce",
                  quantity: 20,
                  unit: "ml",
                  preparation: "",
                  category: "Other",
                  checked: false,
                },
              ],
    }));
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  await userEvent.click(
    await screen.findByRole("button", { name: "Always have light soy sauce" }),
  );
  await waitFor(() =>
    expect(
      screen.queryByRole("button", { name: "Always have light soy sauce" }),
    ).not.toBeInTheDocument(),
  );
  expect(fetch).toHaveBeenCalledWith(
    "/api/shopping/1/staple",
    expect.objectContaining({ method: "POST" }),
  );
  expect(await screen.findByRole("status")).toHaveTextContent(
    "light soy sauce saved as a cupboard staple",
  );
});

it("allows including cupboard staples for a restocking addition", async () => {
  const recipe: Recipe = {
    ...emptyRecipe(),
    id: 1,
    title: "Dinner",
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
  };
  const fetch = vi
    .fn()
    .mockResolvedValue({ ok: true, status: 201, json: async () => [] });
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
  expect(
    screen.getByRole("checkbox", {
      name: "Include cupboard staples this time",
    }),
  ).not.toBeChecked();
  await user.click(
    screen.getByRole("checkbox", {
      name: "Include cupboard staples this time",
    }),
  );
  await user.click(
    screen.getByRole("button", { name: "Add to shopping list" }),
  );
  expect(JSON.parse(fetch.mock.calls[0][1].body).include_staples).toBe(true);
});
