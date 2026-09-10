"use client";

import { Fragment, useState } from "react";
import PageTile from "./PageTile";
import AdSlot from "./AdSlot";
import { pagePath } from "@/lib/seo";
import type { PageSummary } from "@/lib/types";

// Blended into the grid every 6 tiles, matching the spacing Category
// Roundup pages already use for in-feed ads within a recipe-card grid.
const IN_FEED_INTERVAL = 6;

// Section index pages (Recipes, Ingredients, etc.) render as server
// components for the first page of results (so it's part of the initial
// HTML for SEO), then hand off to this client component for "Load more" --
// fetching further pages via /api/pages (a proxy to backend GET /pages,
// since a client component can't reach the server-only API_URL directly).
export default function PagedPageGrid({
  initialPages,
  initialNextOffset,
  initialHasMore,
  templateType,
  pageSize,
}: {
  initialPages: PageSummary[];
  // A raw row cursor from the initial server-rendered fetch (GET /pages
  // with paged=true), not initialPages.length -- see PagedPagesResult's
  // own comment for why those two diverge the moment an unpublished page
  // was skipped, and why re-deriving "more data exists" from the response
  // length (this component's old behavior) let a page with hundreds of
  // real rows stop offering "Load more" after as few as a couple dozen.
  initialNextOffset: number;
  initialHasMore: boolean;
  templateType: string;
  pageSize: number;
}) {
  const [pages, setPages] = useState(initialPages);
  const [offset, setOffset] = useState(initialNextOffset);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(initialHasMore);
  const [error, setError] = useState(false);

  async function loadMore() {
    setLoading(true);
    setError(false);
    try {
      const url = new URL("/api/pages", window.location.origin);
      url.searchParams.set("template_type", templateType);
      url.searchParams.set("limit", String(pageSize));
      url.searchParams.set("offset", String(offset));
      url.searchParams.set("paged", "true");
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to load more");
      const more: { items: PageSummary[]; next_offset: number; has_more: boolean } = await res.json();
      setPages((prev) => [...prev, ...more.items]);
      setOffset(more.next_offset);
      setHasMore(more.has_more);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <ul className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
        {pages.map((page, i) => (
          <Fragment key={page.slug}>
            <li>
              <PageTile
                href={pagePath(page.template_type, page.slug)}
                title={page.title}
                imageQuery={page.hero_image_query ?? page.title}
                imageAlt={page.image_alt}
                imageUrl={page.image_url}
                imageAttribution={page.image_attribution}
              />
            </li>
            {(i + 1) % IN_FEED_INTERVAL === 0 && i !== pages.length - 1 ? (
              <li className="col-span-2 sm:col-span-3">
                <AdSlot variant="in-feed" />
              </li>
            ) : null}
          </Fragment>
        ))}
      </ul>

      {error ? (
        <p className="mt-4 text-center text-sm text-accent">Couldn&apos;t load more, try again.</p>
      ) : null}

      {hasMore ? (
        <div className="mt-8 flex justify-center">
          <button
            type="button"
            onClick={loadMore}
            disabled={loading}
            className="rounded-full border border-ink/20 px-6 py-2.5 text-sm font-semibold hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Loading…" : "Load more"}
          </button>
        </div>
      ) : null}
    </>
  );
}
