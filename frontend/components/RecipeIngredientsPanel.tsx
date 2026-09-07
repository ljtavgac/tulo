"use client";

import { useState } from "react";
import Link from "next/link";
import type { RecipeIngredient } from "@/lib/types";
import { formatUsQuantity, formatMetricQuantity } from "@/lib/format";
import ServingsScaler from "./ServingsScaler";
import UnitToggle, { type Unit } from "./UnitToggle";

export default function RecipeIngredientsPanel({
  ingredients,
  baseServings,
}: {
  ingredients: RecipeIngredient[];
  baseServings: number;
}) {
  const [servings, setServings] = useState(baseServings);
  const [unit, setUnit] = useState<Unit>("us");

  const scale = servings / baseServings;

  return (
    <div className="rounded-lg border border-ink/10 p-4">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-ink/10 pb-3">
        <ServingsScaler servings={servings} onChange={setServings} />
        <UnitToggle unit={unit} onChange={setUnit} />
      </div>

      <ul className="mt-4 space-y-2">
        {ingredients.map((ing) => {
          const qty =
            unit === "us"
              ? formatUsQuantity(ing.base_qty * scale)
              : formatMetricQuantity(ing.base_qty_metric * scale);
          const unitLabel = unit === "us" ? ing.unit_us : ing.unit_metric;

          return (
            <li key={ing.name} className="text-sm">
              <span className="font-medium">
                {qty} {unitLabel}
              </span>{" "}
              {ing.hub_slug ? (
                <Link href={`/ingredients/${ing.hub_slug}`} className="underline hover:text-accent">
                  {ing.name}
                </Link>
              ) : (
                ing.name
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
