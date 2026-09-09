"use client";

import { useState } from "react";
import Link from "next/link";
import type { NutritionPerUnit, PanSize, RecipeIngredient } from "@/lib/types";
import { formatUsQuantity, formatMetricQuantity } from "@/lib/format";
import { pagePath } from "@/lib/seo";
import ServingsScaler from "./ServingsScaler";
import UnitToggle, { type Unit } from "./UnitToggle";
import IngredientUnitConversion from "./IngredientUnitConversion";

type Goal = "" | "lower_calorie" | "higher_protein" | "lower_fat";

const GOAL_OPTIONS: { value: Exclude<Goal, "">; label: string; field: keyof NutritionPerUnit; direction: "min" | "max" }[] = [
  { value: "lower_calorie", label: "Lower calorie", field: "calories", direction: "min" },
  { value: "higher_protein", label: "Higher protein", field: "protein_g", direction: "max" },
  { value: "lower_fat", label: "Lower fat", field: "fat_g", direction: "min" },
];

export default function RecipeIngredientsPanel({
  ingredients,
  baseServings,
  panSize,
  prepTimeMinutes,
  baseCookTimeMinutes,
  baseTotalTimeMinutes,
}: {
  ingredients: RecipeIngredient[];
  baseServings: number;
  // Optional: only recipes actually baked in a shaped pan carry this (see
  // PanSize's own doc comment) -- a cocktail or a skillet sear has none,
  // and the pan-size control below simply doesn't render.
  panSize?: PanSize;
  prepTimeMinutes: number;
  baseCookTimeMinutes: number;
  baseTotalTimeMinutes: number;
}) {
  const [servings, setServings] = useState(baseServings);
  const [unit, setUnit] = useState<Unit>("us");
  // Ingredient name -> name of the substitute currently swapped in for it,
  // if any. A plain lookup against substitute data already embedded in the
  // page (see main.py's available_substitutes), recomputed on every
  // render -- no network call, no instruction-text rewriting, just the
  // displayed name/quantity for that one row. Also what a "goal" (below)
  // writes into in bulk -- both mechanisms share one flat map, so picking
  // a goal and then hand-tweaking one ingredient afterward both just work.
  const [swaps, setSwaps] = useState<Record<string, string>>({});
  const [goal, setGoal] = useState<Goal>("");
  // Which alternative pan (by label) the reader picked, if any -- "" means
  // "as written." Baking-surface-area ratio math: the standard baking
  // reference technique for pan substitution (scale by the ratio of areas
  // to keep the same batter depth in a different footprint), holds only for
  // a same-shape-of-bake swap (loaf-for-loaf, dish-for-dish), which is why
  // PanSize.alternatives is curated per recipe rather than computed from
  // any two pan sizes. Scaling by servings and scaling by pan size are the
  // same underlying operation, "make more or less of this recipe," so they
  // share the one `scale` factor below rather than compounding. Picking a
  // pan takes over from the servings stepper, and moving the stepper hands
  // control back.
  const [panLabel, setPanLabel] = useState("");
  const selectedPan = panSize?.alternatives.find((alt) => alt.label === panLabel);
  const panScale = selectedPan ? selectedPan.area_sq_in / panSize!.current.area_sq_in : null;

  const scale = panScale ?? servings / baseServings;

  const estimatedCookTimeMinutes = panScale != null ? Math.round((baseCookTimeMinutes / panScale) / 5) * 5 : null;
  // Prep effort (chopping, mixing) doesn't scale with batch size the way
  // bake time does -- there's no equivalent of the area-ratio rule for it,
  // so it's shown as authored regardless of pan or servings. Total moves by
  // the same amount cook time did rather than being recomputed as
  // prep+cook, since a recipe's total can include time neither figure
  // covers (mango-ice-cream's freezer time, for one) that should carry
  // through unscaled too.
  const displayedCookTimeMinutes = estimatedCookTimeMinutes ?? baseCookTimeMinutes;
  const displayedTotalTimeMinutes = baseTotalTimeMinutes + (displayedCookTimeMinutes - baseCookTimeMinutes);
  const displayedServings = panScale != null ? Math.max(1, Math.round(baseServings * panScale)) : servings;

  // Ingredients a "goal" can actually act on: the ingredient needs its own
  // nutrition_per_unit (something to compare against) and at least one
  // substitute with both a ratio_multiplier and its own nutrition_per_unit
  // (both needed to compare options apples-to-apples). This is currently a
  // short list -- real substitute data only exists for a pilot ingredient
  // or two -- so the goal picker is deliberately honest about how many
  // ingredients it actually touches rather than implying it reworks the
  // whole recipe.
  const goalAdjustableIngredients = ingredients.filter(
    (ing) => ing.nutrition_per_unit && ing.available_substitutes?.some((sub) => sub.ratio_multiplier != null && sub.nutrition_per_unit)
  );

  function applyGoal(nextGoal: Goal) {
    setGoal(nextGoal);
    if (!nextGoal) {
      setSwaps({});
      return;
    }
    const { field, direction } = GOAL_OPTIONS.find((g) => g.value === nextGoal)!;
    const nextSwaps: Record<string, string> = {};
    for (const ing of goalAdjustableIngredients) {
      const options: { name: string | null; value: number }[] = [
        { name: null, value: ing.nutrition_per_unit![field] },
        ...ing
          .available_substitutes!.filter((sub) => sub.ratio_multiplier != null && sub.nutrition_per_unit)
          .map((sub) => ({ name: sub.name, value: sub.nutrition_per_unit![field] * sub.ratio_multiplier! })),
      ];
      const best = options.reduce((a, b) => {
        const bIsBetter = direction === "min" ? b.value < a.value : b.value > a.value;
        return bIsBetter ? b : a;
      });
      if (best.name) nextSwaps[ing.name] = best.name;
    }
    setSwaps(nextSwaps);
  }

  // Live nutrition PER SERVING, using the same swaps state as the
  // ingredient list above -- but deliberately NOT the servings scale.
  // Nutrition facts are conventionally a per-serving figure that doesn't
  // move when you double a recipe (the whole batch doubles, but a serving
  // is still a serving), so this always divides by baseServings rather
  // than the current, user-adjustable `servings`. It only recalculates
  // when a swap changes which ingredient's numbers are active -- not when
  // the serving slider moves, which would otherwise read as the recipe
  // itself getting more or less nutritious just from being scaled. Only
  // ingredients with nutrition_per_unit data contribute (currently a pilot
  // batch of recipes, not all of them); if none do, `hasData` stays false
  // and no block is shown.
  const nutritionTotals = ingredients.reduce(
    (totals, ing) => {
      const activeSubstitute = ing.available_substitutes?.find((sub) => sub.name === swaps[ing.name]);
      const perUnit = activeSubstitute?.nutrition_per_unit ?? ing.nutrition_per_unit;
      if (!perUnit) return totals;
      const multiplier = activeSubstitute?.ratio_multiplier ?? 1;
      const amountPerServing = (ing.base_qty * multiplier) / baseServings;
      return {
        calories: totals.calories + amountPerServing * perUnit.calories,
        protein_g: totals.protein_g + amountPerServing * perUnit.protein_g,
        carbs_g: totals.carbs_g + amountPerServing * perUnit.carbs_g,
        fat_g: totals.fat_g + amountPerServing * perUnit.fat_g,
        hasData: true,
      };
    },
    { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0, hasData: false }
  );

  return (
    <>
      {/* Mirrors the ingredients box's own scale state, not the recipe's
          authored figures, so this never shows a Cook/Total/Servings that
          contradicts what the panel below is actually displaying. */}
      <dl className="mt-4 grid grid-cols-2 gap-3 rounded-lg border border-ink/10 p-4 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-ink/50">Prep</dt>
          <dd className="font-semibold">{prepTimeMinutes} min</dd>
        </div>
        <div>
          <dt className="text-ink/50">Cook</dt>
          <dd className="font-semibold">{displayedCookTimeMinutes} min</dd>
        </div>
        <div>
          <dt className="text-ink/50">Total</dt>
          <dd className="font-semibold">{displayedTotalTimeMinutes} min</dd>
        </div>
        <div>
          <dt className="text-ink/50">Servings</dt>
          <dd className="font-semibold">{displayedServings}</dd>
        </div>
      </dl>

      <h2 className="mt-6 text-xl font-bold">Ingredients</h2>
      <div className="mt-3 rounded-lg border border-ink/10 p-4">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-ink/10 pb-3">
          <ServingsScaler
            servings={displayedServings}
            onChange={(next) => {
              setPanLabel("");
              setServings(next);
            }}
          />
          <UnitToggle unit={unit} onChange={setUnit} />
        </div>

        {panSize && panSize.alternatives.length > 0 ? (
          <div className="border-b border-ink/10 py-3 text-sm">
            <label className="flex flex-wrap items-center gap-2">
              <span className="font-medium">Using a different pan?</span>
              <select
                value={panLabel}
                onChange={(e) => setPanLabel(e.target.value)}
                className="rounded border border-ink/15 bg-ink/[0.02] px-2 py-1 text-xs text-ink/70"
              >
                <option value="">As written ({panSize.current.label})</option>
                {panSize.alternatives.map((alt) => (
                  <option key={alt.label} value={alt.label}>
                    {alt.label}
                  </option>
                ))}
              </select>
            </label>
            {selectedPan ? (
              <p className="mt-1 text-xs text-ink/40">
                Ingredients and the Prep/Cook/Total/Servings figures above are now scaled to fill a {selectedPan.label} at roughly the
                same depth as written. The adjusted cook time is a starting point based on pan area, not a guarantee -- start checking a
                few minutes early and test for doneness rather than trusting the clock alone.
              </p>
            ) : null}
          </div>
        ) : null}

        {goalAdjustableIngredients.length > 0 ? (
          <div className="border-b border-ink/10 py-3 text-sm">
            <label className="flex flex-wrap items-center gap-2">
              <span className="text-ink/60">Adjust for:</span>
              <select
                value={goal}
                onChange={(e) => applyGoal(e.target.value as Goal)}
                className="rounded border border-ink/15 bg-ink/[0.02] px-2 py-1 text-xs text-ink/70"
              >
                <option value="">No goal</option>
                {GOAL_OPTIONS.map((g) => (
                  <option key={g.value} value={g.value}>
                    {g.label}
                  </option>
                ))}
              </select>
            </label>
            {goal ? (
              <p className="mt-1 text-xs text-ink/40">
                Swapped {Object.keys(swaps).length} of {goalAdjustableIngredients.length} ingredient
                {goalAdjustableIngredients.length === 1 ? "" : "s"} with substitute data for this goal
                {ingredients.length > goalAdjustableIngredients.length
                  ? `; the rest of this recipe's ingredients don't have substitute data to adjust`
                  : ""}
                .
              </p>
            ) : null}
          </div>
        ) : null}

        <ul className="mt-4 space-y-2">
          {ingredients.map((ing) => {
            const activeSubstitute = ing.available_substitutes?.find((sub) => sub.name === swaps[ing.name]);
            // Defaults to 1 (no change) when nothing's swapped in -- the
            // substitute's ratio_multiplier is "amount of substitute per 1
            // unit of the original," so it multiplies the same base_qty the
            // serving scaler already scales, rather than replacing it.
            const multiplier = activeSubstitute?.ratio_multiplier ?? 1;

            // unit_metric === unit_us marks a count of discrete items (eggs,
            // bananas, cloves of garlic) rather than a real unit conversion --
            // there's no meaningful weight/volume equivalent for "1 banana",
            // so both views show the same fraction-formatted count instead of
            // one side rounding to whole grams (which could round a small
            // fractional count down to a nonsensical "0").
            const isCount = ing.unit_metric === ing.unit_us;
            const rawQty = unit === "us" || isCount ? ing.base_qty * scale * multiplier : ing.base_qty_metric * scale * multiplier;
            const qty = unit === "us" || isCount ? formatUsQuantity(rawQty) : formatMetricQuantity(rawQty);
            const unitLabel = unit === "us" || isCount ? ing.unit_us : ing.unit_metric;
            const displayName = activeSubstitute ? activeSubstitute.name : ing.name;

            return (
              <li key={ing.name} className="text-sm">
                <div>
                  <span className="font-medium">
                    {qty} {unitLabel}
                  </span>
                  <IngredientUnitConversion amount={rawQty} unit={unitLabel} />{" "}
                  {!activeSubstitute && ing.hub_slug ? (
                    <Link href={pagePath("ingredient_hub", ing.hub_slug)} className="underline hover:text-accent">
                      {displayName}
                    </Link>
                  ) : (
                    displayName
                  )}
                </div>

                {ing.available_substitutes && ing.available_substitutes.length > 0 ? (
                  <select
                    value={swaps[ing.name] ?? ""}
                    onChange={(e) => {
                      const value = e.target.value;
                      setSwaps((prev) => {
                        const next = { ...prev };
                        if (value) next[ing.name] = value;
                        else delete next[ing.name];
                        return next;
                      });
                    }}
                    className="mt-1 rounded border border-ink/15 bg-ink/[0.02] px-2 py-0.5 text-xs text-ink/60"
                  >
                    <option value="">I don&apos;t have {ing.name}?</option>
                    {ing.available_substitutes.map((sub) => (
                      <option key={sub.name} value={sub.name}>
                        Use {sub.name} instead
                      </option>
                    ))}
                  </select>
                ) : null}
              </li>
            );
          })}
        </ul>

        {nutritionTotals.hasData ? (
          <div className="mt-4 rounded border border-ink/10 bg-ink/[0.02] p-3 text-sm">
            <p className="font-medium">Nutrition per serving</p>
            <dl className="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 text-ink/70 sm:grid-cols-4">
              <div className="flex justify-between gap-2 sm:block">
                <dt className="text-ink/50">Calories</dt>
                <dd>{Math.round(nutritionTotals.calories)}</dd>
              </div>
              <div className="flex justify-between gap-2 sm:block">
                <dt className="text-ink/50">Protein</dt>
                <dd>{Math.round(nutritionTotals.protein_g)}g</dd>
              </div>
              <div className="flex justify-between gap-2 sm:block">
                <dt className="text-ink/50">Carbs</dt>
                <dd>{Math.round(nutritionTotals.carbs_g)}g</dd>
              </div>
              <div className="flex justify-between gap-2 sm:block">
                <dt className="text-ink/50">Fat</dt>
                <dd>{Math.round(nutritionTotals.fat_g)}g</dd>
              </div>
            </dl>
            <p className="mt-1 text-xs text-ink/40">
              Based on the recipe as written, one serving. Recalculates if you swap an ingredient above. An estimate only, exact values
              depend on the specific ingredients used.
            </p>
          </div>
        ) : null}
      </div>
    </>
  );
}
