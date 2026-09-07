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
// hitting Enter with no suggestion highlighted navigates to the full
// results page exactly as before. On top of that, this adds a debounced
// autocomplete dropdown with thumbnails, navigable by mouse or keyboard,
// so a query can be resolved without ever leaving the current page.
export default function SearchBox() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PageSummary[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setActiveIndex(-1);

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

  useEffect(() => {
    if (activeIndex >= 0) itemRefs.current[activeIndex]?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  const dropdownOpen = open && query.trim() && results.length > 0;

  function goTo(page: PageSummary) {
    setOpen(false);
    router.push(pagePath(page.template_type, page.slug));
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!dropdownOpen) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => (i + 1) % results.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => (i <= 0 ? results.length - 1 : i - 1));
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      goTo(results[activeIndex]);
    } else if (e.key === "Escape") {
      setOpen(false);
      setActiveIndex(-1);
    }
  }

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
        onKeyDown={handleKeyDown}
        role="combobox"
        aria-expanded={Boolean(dropdownOpen)}
        aria-controls="search-suggestions"
        aria-activedescendant={activeIndex >= 0 ? `search-suggestion-${activeIndex}` : undefined}
        placeholder="Search…"
        className="w-full bg-transparent text-base outline-none placeholder:text-ink/40 sm:text-sm"
      />

      {dropdownOpen ? (
        <ul
          id="search-suggestions"
          role="listbox"
          className="absolute left-0 right-0 top-full z-50 mt-2 max-h-96 overflow-y-auto rounded-lg border border-ink/10 bg-white shadow-lg"
        >
          {results.map((page, i) => (
            <li key={page.slug} role="presentation">
              <button
                id={`search-suggestion-${i}`}
                role="option"
                aria-selected={i === activeIndex}
                ref={(el) => {
                  itemRefs.current[i] = el;
                }}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onMouseEnter={() => setActiveIndex(i)}
                onClick={() => goTo(page)}
                className={`flex w-full items-center gap-3 px-3 py-2 text-left ${
                  i === activeIndex ? "bg-ink/5" : "hover:bg-ink/5"
                }`}
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
