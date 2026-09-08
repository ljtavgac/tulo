"use client";

import { useState } from "react";
import { convertToOtherUnits, getConvertibleUnit } from "@/lib/conversions";

// A clickable unit on a recipe ingredient, showing that same amount
// converted to a few other common units on the spot -- no navigation to
// the standalone Conversion Calculator page. Pure client-side math against
// lib/conversions.ts, the exact same data and ratios that tool page uses.
// Renders nothing for a unit that isn't unambiguously convertible (see
// getConvertibleUnit) rather than guessing.
export default function IngredientUnitConversion({ amount, unit }: { amount: number; unit: string }) {
  const [open, setOpen] = useState(false);
  const convertible = getConvertibleUnit(unit);
  if (!convertible) return null;

  const conversions = convertToOtherUnits(amount, convertible.category, convertible.canonical);

  return (
    <span className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={`Convert ${unit} to other units`}
        className="ml-1 rounded text-ink/35 hover:text-accent"
      >
        ⇄
      </button>
      {open ? (
        <span
          role="dialog"
          className="absolute left-1/2 top-full z-20 mt-1 w-40 -translate-x-1/2 rounded-lg border border-ink/10 bg-white p-2 text-xs shadow-lg"
        >
          {conversions.map((c) => (
            <span key={c.unit} className="flex items-baseline justify-between gap-2 py-0.5">
              <span className="text-ink/50">
                {c.unit}
                {c.amount === 1 ? "" : "s"}
              </span>
              <span className="font-medium">{c.amount}</span>
            </span>
          ))}
        </span>
      ) : null}
    </span>
  );
}
