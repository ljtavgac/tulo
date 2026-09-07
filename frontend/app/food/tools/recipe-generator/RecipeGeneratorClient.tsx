"use client";

import { useState } from "react";
import Link from "next/link";
import Breadcrumbs from "@/components/Breadcrumbs";
import JsonLd from "@/components/JsonLd";
import { buildBreadcrumbList, pagePath } from "@/lib/seo";

const BREADCRUMB_ITEMS = [
  { label: "Home", href: "/" },
  { label: "Food", href: "/food" },
  { label: "Tools", href: "/food/tools" },
  { label: "Custom Recipe Generator" },
];

interface Match {
  slug: string;
  title: string;
  matched_count: number;
  requested_count: number;
  total_ingredients: number;
}

// There's no LLM wired into this stack to generate a brand-new recipe from
// scratch, so rather than faking that, this calls /api/recipe-match (a
// proxy to backend GET /recipes/match) and shows real recipes already on
// Tulo ranked by how many of the given ingredients they use -- an honest,
// working recommendation that gets better as more recipes get published.
export default function RecipeGeneratorClient() {
  const [ingredients, setIngredients] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [matches, setMatches] = useState<Match[]>([]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!ingredients.trim()) return;

    setStatus("loading");
    try {
      const url = new URL("/api/recipe-match", window.location.origin);
      url.searchParams.set("ingredients", ingredients);
      const res = await fetch(url);
      if (!res.ok) throw new Error("Request failed");
      const data: Match[] = await res.json();
      setMatches(data);
      setStatus("done");
    } catch {
      setStatus("error");
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-8">
      <Breadcrumbs items={BREADCRUMB_ITEMS} />
      <JsonLd data={buildBreadcrumbList(BREADCRUMB_ITEMS)} />
      <h1 className="mt-4 text-3xl font-bold">Custom Recipe Generator</h1>
      <p className="mt-3 text-ink/70">
        Tell us what you have on hand, and we&apos;ll match it against real recipes on Tulo.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4 rounded-lg border border-ink/10 p-4">
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

        <button
          type="submit"
          disabled={!ingredients.trim() || status === "loading"}
          className="w-full rounded-full bg-ink px-4 py-2 text-sm font-semibold text-cream transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {status === "loading" ? "Finding recipes…" : "Find Recipes"}
        </button>
      </form>

      {status === "error" ? (
        <p className="mt-6 text-sm text-accent">
          Something went wrong finding recipes for that. Try again in a moment.
        </p>
      ) : null}

      {status === "done" && matches.length === 0 ? (
        <p className="mt-6 text-sm text-ink/70">
          No recipes on Tulo currently use those ingredients. Try a different combination, or check back as
          more recipes get published.
        </p>
      ) : null}

      {matches.length > 0 ? (
        <ul className="mt-6 space-y-3">
          {matches.map((match) => (
            <li key={match.slug}>
              <Link
                href={pagePath("recipe_or_dish", match.slug)}
                className="block rounded-lg border border-ink/10 p-4 hover:border-accent"
              >
                <p className="font-semibold">{match.title}</p>
                <p className="mt-1 text-sm text-ink/60">
                  Uses {match.matched_count} of your {match.requested_count} ingredient
                  {match.requested_count === 1 ? "" : "s"} ({match.total_ingredients} total in the recipe)
                </p>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </main>
  );
}
