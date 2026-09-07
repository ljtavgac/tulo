"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import StockPhotoSlot from "./StockPhotoSlot";
import { pagePath } from "@/lib/seo";
import type { PageSummary } from "@/lib/types";

const TEMPLATE_LABELS: Record<string, string> = {
  recipe_or_dish: "Recipe",
  ingredient_hub: "Ingredient",
  howto_technique: "How-To",
  definition: "Definition",
  comparison: "Comparison",
  substitute: "Substitute",
  category_roundup: "Collection",
  tool_page: "Tool",
};

// A plain GET form (action="/food/search") that still works with no JS --
// hitting Enter navigates to the full results page exactly as before. On
// top of that, this adds a debounced autocomplete dropdown with thumbnails
// so a query can be resolved without ever leaving the current page.
export default function SearchBox() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PageSummary[]>([]);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      try {
        const url = new URL("/api/search-suggest", window.location.origin);
        url.searchParams.set("q", trimmed);
        const res = await fetch(url);
        if (!res.ok) return;
        setResults(await res.json());
      } catch {
        // Autocomplete is a convenience -- a failed fetch just means no
        // dropdown, submitting the form still falls back to a real search.
      }
    }, 250);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  return (
    <form
      role="search"
      action="/food/search"
      autoComplete="off"
      className="relative ml-auto flex min-w-[10rem] flex-1 items-center gap-2 rounded-full border border-ink/15 bg-white px-3.5 py-2 sm:flex-none sm:basis-64 focus-within:border-accent"
    >
      <svg aria-hidden viewBox="0 0 20 20" fill="none" className="h-4 w-4 shrink-0 text-ink/40">
        <circle cx="9" cy="9" r="6" stroke="currentColor" strokeWidth="1.5" />
        <path d="M13.5 13.5L17.5 17.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      <input
        type="search"
        name="q"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder="Search recipes…"
        className="w-full bg-transparent text-sm outline-none placeholder:text-ink/40"
      />

      {open && query.trim() && results.length > 0 ? (
        <ul className="absolute left-0 right-0 top-full z-50 mt-2 max-h-96 overflow-y-auto rounded-lg border border-ink/10 bg-white shadow-lg">
          {results.map((page) => (
            <li key={page.slug}>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => router.push(pagePath(page.template_type, page.slug))}
                className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-cream"
              >
                <div className="h-12 w-12 shrink-0 overflow-hidden rounded">
                  <StockPhotoSlot
                    query={page.hero_image_query ?? page.title}
                    imageUrl={page.image_url}
                    aspect="thumbnail"
                    compact
                  />
                </div>
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold">{page.title}</span>
                  <span className="block text-xs uppercase tracking-wide text-ink/40">
                    {TEMPLATE_LABELS[page.template_type] ?? page.template_type}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </form>
  );
}
