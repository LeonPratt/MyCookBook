import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ImportPanel from "./ImportPanel";
import { emptyRecipe } from "./types";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

async function review(duplicate = false, batch = false) {
  const recipe = { ...emptyRecipe(), title: "Lemon chicken" };
  const fetch = vi.fn().mockImplementation(async (path: string) => ({
    ok: true, status: 200,
    json: async () => path.endsWith("/preview") ? [{
      index: 0, recipe,
      duplicates: duplicate && !batch ? [{ ...recipe, id: 1 }] : [],
      duplicate_indices: batch ? [1] : [],
    }] : { imported: 1 },
  }));
  vi.stubGlobal("fetch", fetch);
  const onDone = vi.fn();
  render(<ImportPanel llm={false} onRecipe={vi.fn()} onDone={onDone} onError={vi.fn()} />);
  const user = userEvent.setup();
  await user.click(screen.getByRole("textbox", { name: "Recipe JSON" }));
  await user.paste(JSON.stringify(recipe));
  await user.click(screen.getByRole("button", { name: "Review import" }));
  await screen.findByRole("heading", { name: recipe.title });
  return { fetch, user, onDone };
}

it("imports new recipes without an action selector or backup restoration checkbox", async () => {
  const { fetch, user, onDone } = await review();
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Import selected recipes" }));
  await waitFor(() => expect(onDone).toHaveBeenCalled());
  const payload = JSON.parse(fetch.mock.lastCall![1].body);
  expect(payload.actions).toEqual({ "0": "separate" });
  expect(payload).not.toHaveProperty("restore_personal");
  expect(payload).not.toHaveProperty("restore_settings");
});

it.each([false, true])("requires renaming when keeping a duplicate (batch: %s)", async (batch) => {
  const { fetch, user } = await review(true, batch);
  expect(screen.getByRole("alert")).toHaveTextContent("Duplicate name detected");
  await user.selectOptions(screen.getByRole("combobox", { name: "Import action" }), "separate");
  const save = screen.getByRole("button", { name: "Import selected recipes" });
  expect(save).toBeDisabled();
  const name = screen.getByRole("textbox", { name: /New name for imported recipe/ });
  await user.type(name, "lemon CHICKEN");
  expect(save).toBeDisabled();
  await user.clear(name);
  await user.type(name, "My chicken variation");
  expect(save).toBeEnabled();
  await user.click(save);
  expect(JSON.parse(fetch.mock.lastCall![1].body).renames).toEqual({ "0": "My chicken variation" });
});

it("lets an existing duplicate be replaced without renaming", async () => {
  const { fetch, user } = await review(true);
  await user.selectOptions(screen.getByRole("combobox", { name: "Import action" }), "replace");
  expect(screen.queryByRole("textbox", { name: /New name/ })).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Import selected recipes" }));
  expect(JSON.parse(fetch.mock.lastCall![1].body).actions).toEqual({ "0": "replace" });
});
