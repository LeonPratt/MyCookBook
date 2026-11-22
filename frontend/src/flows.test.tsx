import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RecipeDetail from "./RecipeDetail";
import RecipeForm from "./RecipeForm";
import ImportPanel from "./ImportPanel";
import { emptyRecipe, Recipe } from "./types";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
const example = (): Recipe => ({
  ...emptyRecipe(),
  id: 7,
  title: "Simple supper",
  ingredients: [
    {
      name: "rice",
      quantity: 100,
      unit: "g",
      optional: false,
      preparation: "",
      group: "",
      category: "Pantry",
    },
  ],
  instructions: [
    { text: "Rinse the rice.", timer_seconds: null },
    { text: "Cook until tender.", timer_seconds: null },
  ],
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
});
describe("primary kitchen flows", () => {
  it("moves through cooking steps and offers a completed meal record", async () => {
    const user = userEvent.setup();
    render(
      <RecipeDetail
        recipe={example()}
        onUpdate={() => {}}
        onEdit={() => {}}
        onBack={() => {}}
        notify={() => {}}
        onError={() => {}}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Start cooking" }));
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "1",
    );
    expect(
      screen.getByRole("button", { name: "Previous step" }),
    ).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Show ingredients" }));
    expect(screen.getByRole("checkbox")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next step" }));
    expect(screen.getByText("Cook until tender.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Finish cooking" }));
    expect(
      screen.getByRole("dialog", { name: "A meal worth remembering" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Record cooked meal" }),
    ).toBeInTheDocument();
  });
  it("creates a recipe through structured fields, retaining blank quantities", async () => {
    const user = userEvent.setup();
    const save = vi.fn(),
      error = vi.fn();
    const fetch = vi
      .fn()
      .mockResolvedValue({
        ok: true,
        status: 201,
        json: async () => example(),
      });
    vi.stubGlobal("fetch", fetch);
    render(
      <RecipeForm
        initial={emptyRecipe()}
        onSave={save}
        onCancel={() => {}}
        onError={error}
      />,
    );
    await user.type(screen.getByLabelText("Recipe title"), "Herbed rice");
    await user.type(screen.getByLabelText("Name"), "rice");
    await user.type(screen.getByLabelText("Instruction"), "Cook until tender.");
    await user.click(screen.getByRole("button", { name: "Save recipe" }));
    expect(error).not.toHaveBeenCalled();
    expect(save).toHaveBeenCalled();
    const request = JSON.parse(fetch.mock.calls[0][1].body);
    expect(request.ingredients[0].quantity).toBeNull();
    expect(request.instructions[0].text).toBe("Cook until tender.");
    expect(request.title).toBe("Herbed rice");
  });
  it("requires duplicate review and submits the chosen replacement action", async () => {
    const user = userEvent.setup(),
      done = vi.fn(),
      error = vi.fn();
    const r = example();
    const fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => [{ index: 0, recipe: r, duplicates: [r] }],
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ imported: 1 }),
      });
    vi.stubGlobal("fetch", fetch);
    render(
      <ImportPanel
        llm={false}
        onRecipe={() => {}}
        onDone={done}
        onError={error}
      />,
    );
    await user.type(screen.getByLabelText("Recipe JSON"), "[[]]"); // Replace with exact JSON via paste-compatible clear/type.
    await user.clear(screen.getByLabelText("Recipe JSON"));
    await user.click(screen.getByLabelText("Recipe JSON"));
    await user.paste(JSON.stringify(r));
    await user.click(screen.getByRole("button", { name: "Review import" }));
    expect(done).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Import action")).toHaveValue("skip");
    await user.selectOptions(screen.getByLabelText("Import action"), "replace");
    await user.click(
      screen.getByRole("button", { name: "Import selected recipes" }),
    );
    expect(done).toHaveBeenCalled();
    expect(error).not.toHaveBeenCalled();
    expect(JSON.parse(fetch.mock.calls[1][1].body).actions).toEqual({
      "0": "replace",
    });
  });
});
