"use client";

import { useState } from "react";
import Link from "next/link";
import type { RecipeIngredient } from "@/lib/types";
import { formatUsQuantity, formatMetricQuantity } from "@/lib/format";
import { pagePath } from "@/lib/seo";
import ServingsScaler from "./ServingsScaler";
import UnitToggle, { type Unit } from "./UnitToggle";
import IngredientUnitConversion from "./IngredientUnitConversion";

export default function RecipeIngredientsPanel({
  ingredients,
  baseServings,
}: {
  ingredients: RecipeIngredient[];
  baseServings: number;
}) {
  const [servings, setServings] = useState(baseServings);
  const [unit, setUnit] = useState<Unit>("us");
  // Ingredient name -> name of the substitute currently swapped in for it,
  // if any. A plain lookup against substitute data already embedded in the
  // page (see main.py's available_substitutes), recomputed on every
  // render -- no network call, no instruction-text rewriting, just the
  // displayed name/quantity for that one row.
  const [swaps, setSwaps] = useState<Record<string, string>>({});

  const scale = servings / baseServings;

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
    <div className="rounded-lg border border-ink/10 p-4">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-ink/10 pb-3">
        <ServingsScaler servings={servings} onChange={setServings} />
        <UnitToggle unit={unit} onChange={setUnit} />
      </div>

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
            Based on the recipe as written, one serving. Recalculates if you swap an ingredient above. An estimate only, exact values depend on the specific ingredients used.
          </p>
        </div>
      ) : null}
    </div>
  );
}
