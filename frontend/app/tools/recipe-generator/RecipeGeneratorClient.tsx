"use client";

import { useState } from "react";

// Page shell only -- no generation logic wired up yet. PAGE_TEMPLATES.md
// calls this tool lower-priority ("more competitive, more of a
// retention/differentiation feature; build last"), so this round just
// establishes the input UI to review, not the generation itself.
export default function RecipeGeneratorClient() {
  const [ingredients, setIngredients] = useState("");
  const [mealType, setMealType] = useState("Any");

  return (
    <main className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="text-3xl font-bold">Custom Recipe Generator</h1>
      <p className="mt-3 text-ink/70">
        Tell us what you have on hand, and we&apos;ll put together a recipe idea.
      </p>

      <form
        onSubmit={(e) => e.preventDefault()}
        className="mt-6 space-y-4 rounded-lg border border-ink/10 p-4"
      >
        <label className="block text-sm font-medium">
          Ingredients you have
          <textarea
            value={ingredients}
            onChange={(e) => setIngredients(e.target.value)}
            placeholder="e.g. chicken thighs, spinach, feta, lemon"
            rows={3}
            className="mt-1 w-full rounded border border-ink/20 px-3 py-2 text-sm focus:border-accent focus:outline-none"
          />
        </label>

        <label className="block text-sm font-medium">
          Meal type
          <select
            value={mealType}
            onChange={(e) => setMealType(e.target.value)}
            className="mt-1 w-full rounded border border-ink/20 px-3 py-2 text-sm"
          >
            <option>Any</option>
            <option>Breakfast</option>
            <option>Lunch</option>
            <option>Dinner</option>
            <option>Snack</option>
            <option>Dessert</option>
          </select>
        </label>

        <button
          type="button"
          disabled
          title="Generation logic not built yet -- this is a page-shell review only"
          className="w-full cursor-not-allowed rounded-full border-2 border-dashed border-ink/20 px-4 py-2 text-sm font-semibold text-ink/50"
        >
          Generate Recipe (coming soon)
        </button>
      </form>
    </main>
  );
}
