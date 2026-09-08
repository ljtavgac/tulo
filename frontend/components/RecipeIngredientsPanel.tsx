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
    </div>
  );
}
