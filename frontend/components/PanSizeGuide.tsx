"use client";

import { useState } from "react";
import type { PanSize } from "@/lib/types";

// Pan substitution math (area ratios, and the inverse relationship between
// footprint and bake time) is a standard baking reference technique, but
// real ovens and pan materials vary enough that the resulting time is a
// starting estimate, never a guarantee -- framed that way throughout,
// matching the same "estimate only" honesty already used for nutrition.
export default function PanSizeGuide({ panSize, cookTimeMinutes }: { panSize: PanSize; cookTimeMinutes: number }) {
  const [selectedLabel, setSelectedLabel] = useState("");
  const selected = panSize.alternatives.find((alt) => alt.label === selectedLabel);

  const scaleFactor = selected ? selected.area_sq_in / panSize.current.area_sq_in : 1;
  const estimatedMinutes = selected ? Math.round(cookTimeMinutes / scaleFactor / 5) * 5 : cookTimeMinutes;
  const minuteDelta = estimatedMinutes - cookTimeMinutes;

  return (
    <div className="mt-4 rounded border border-ink/10 bg-ink/[0.02] p-3 text-sm">
      <label className="block">
        <span className="font-medium">Using a different pan?</span>{" "}
        <select
          value={selectedLabel}
          onChange={(e) => setSelectedLabel(e.target.value)}
          className="mt-1 block rounded border border-ink/15 bg-white px-2 py-1 text-xs text-ink/70 sm:mt-0 sm:inline-block sm:w-auto"
        >
          <option value="">As written ({panSize.current.label})</option>
          {panSize.alternatives.map((alt) => (
            <option key={alt.label} value={alt.label}>
              {alt.label}
            </option>
          ))}
        </select>
      </label>

      {selected ? (
        <div className="mt-2 text-ink/70">
          <p>
            Scale the recipe to about <span className="font-semibold text-ink">{Math.round(scaleFactor * 100)}%</span> to fill a{" "}
            {selected.label} at roughly the same depth as written.
          </p>
          <p className="mt-1">
            Estimated bake time: <span className="font-semibold text-ink">~{estimatedMinutes} min</span>{" "}
            <span className="text-ink/50">
              ({minuteDelta > 0 ? `about ${minuteDelta} min more` : `about ${-minuteDelta} min less`} than the original {cookTimeMinutes} min)
            </span>
          </p>
          <p className="mt-1 text-xs text-ink/40">
            A starting point based on pan area, not a guarantee, pan material and your oven both affect actual timing. Start checking a
            few minutes early and test for doneness rather than trusting the clock alone.
          </p>
        </div>
      ) : null}
    </div>
  );
}
