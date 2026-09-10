"use client";

import { useState } from "react";
import Image from "next/image";
import type { ImageAttribution } from "@/lib/types";

// Renders a real photo (sourced by backend/app/fetch_stock_images.py via
// Unsplash/Pexels) with required attribution once one exists for this
// page. Renders nothing at all otherwise -- a page whose photo hasn't been
// fetched yet (a brand new page before the next fetch_images() run, or a
// stock search that came up empty) shows no image rather than a dashed
// "Stock photo slot" placeholder box, which read as an obviously
// unfinished part of the page to a real visitor. Nothing about call sites
// needs to change based on which state a given page is in.
//
// A client component (not the plain server component this used to be)
// specifically for the onError handler below: a URL can be well-formed and
// on an allowlisted host, get written to the database, and *still* fail to
// actually load in a browser (the source photo gets taken down at the
// provider, a CDN edge hiccups, a hotlink check rejects the referrer) --
// nothing on the backend can ever fully rule that out ahead of time, so
// this is the one place that can actually see the failure happen and hide
// it, the same way a missing imageUrl already hides instead of showing a
// broken image icon.
//
// `unoptimized`: Unsplash/Pexels URLs are already pre-sized via their own
// query params (see backend/app/images.py -- "regular"/"large" variants,
// not full-resolution originals), so there's nothing for Next's own image
// optimizer to usefully add here, only another hop that can fail on its
// own -- a request that goes through Vercel's optimizer pipeline instead
// of straight to the source CDN, and one subject to that pipeline's own
// separate quota/availability, distinct from Unsplash/Pexels ever being
// down. Skipping it removes that whole extra failure surface for photos
// that don't need it.
export default function StockPhotoSlot({
  query,
  alt,
  imageUrl,
  attribution,
  aspect = "hero",
  className = "",
  reserveSpace = false,
  showAttribution = true,
  priority = false,
}: {
  query: string;
  // Real, specific caption text (e.g. a recipe's own meta_description),
  // distinct from `query` (the term used to search Unsplash/Pexels for
  // this photo in the first place). Falls back to `query` when absent --
  // every hero photo on the site has a real image_alt now (see the SEO
  // audit that found every photo's alt text was literally just its search
  // query), but this fallback keeps any caller that hasn't been threaded
  // through yet (or a future one) from ending up with no alt text at all.
  alt?: string | null;
  imageUrl?: string;
  attribution?: ImageAttribution;
  aspect?: "hero" | "thumbnail";
  className?: string;
  // Grid contexts (PageTile, RecipeCard) need every card the same height
  // whether or not its photo ever got fetched -- collapsing straight to
  // the title text otherwise makes a missing-photo card visibly shorter
  // than its photographed neighbors in the same row. A single hero image
  // on its own page has no row to stay aligned with, so it keeps the
  // original "nothing at all" behavior by default.
  reserveSpace?: boolean;
  // Next's <Image> defaults to loading="lazy" (native intersection-observer
  // based deferral) for every image, StockPhotoSlot included -- fine for a
  // grid thumbnail below the fold, wrong for the single hero photo that
  // sits right under <h1> on a recipe/ingredient/how-to/etc. page: that one
  // is almost always the page's LCP element, and lazy-loading it means the
  // browser doesn't even start the request until it's done parsing down to
  // this element, instead of discovering and prioritizing it immediately.
  // Callers that render the one hero image for a standalone content page
  // should set this; grid/thumbnail call sites (PageTile-style contexts,
  // search results) should leave it false.
  priority?: boolean;
  // The attribution figcaption below renders a real <a> link to the
  // photographer's profile. PageTile and RecipeCard are themselves always
  // (or conditionally) wrapped in their own outer <Link> to the page --
  // an <a> nested inside another <a> is invalid HTML, and browsers
  // "repair" it during parsing by closing the outer anchor early, which
  // makes the actual DOM diverge from what React rendered and throws a
  // hydration error (React error #418) on every tile that has a real
  // fetched photo -- confirmed by reproducing it locally with a real
  // image_url set on a homepage tile (no error with no photo, reliably
  // reproduced with one). A failed hydration discards and re-renders that
  // whole subtree client-side, which is what was actually behind
  // carousel tiles rendering inconsistently -- not a caching issue. A
  // single hero image on its own page (not wrapped in an outer Link) has
  // no such conflict and keeps showing attribution, as required by
  // Unsplash's API terms.
  showAttribution?: boolean;
}) {
  const [failed, setFailed] = useState(false);

  const aspectClass = aspect === "hero" ? "aspect-[16/9]" : "aspect-square";

  if (!imageUrl || failed) {
    // No placeholder at all outside a grid (reserveSpace false): the single
    // hero image on its own page just renders nothing, same as always. In a
    // grid, an empty box reads as a rendering bug next to photographed
    // neighbors -- a generic "photo not loaded" glyph (not an attempt to
    // represent the specific missing subject) reads as "content pending"
    // instead. Never shown for a real photo that failed to load after
    // fetch_stock_images.py wrote a good URL (see the onError comment
    // above) vs. one that was never fetched -- StockPhotoSlot doesn't
    // distinguish the two today, and this placeholder is a reasonable
    // stand-in for both.
    if (!reserveSpace) return null;
    return (
      <div className={`flex items-center justify-center ${aspectClass} rounded-lg bg-ink/5 ${className}`}>
        <svg
          viewBox="0 0 48 48"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="round"
          className="h-[30%] w-[30%] text-ink/20"
          aria-hidden="true"
        >
          <rect x="6" y="9" width="36" height="30" rx="3" />
          <circle cx="17" cy="19" r="3.4" />
          <path d="M6 33l11-11 8 8 6-6 11 11" strokeLinecap="round" />
        </svg>
      </div>
    );
  }

  return (
    <figure className={className}>
      <div className={`relative ${aspectClass} overflow-hidden rounded-lg bg-ink/5`}>
        <Image
          src={imageUrl}
          alt={alt || query}
          fill
          unoptimized
          priority={priority}
          sizes="(min-width: 1024px) 640px, 100vw"
          className="object-cover"
          onError={() => setFailed(true)}
        />
      </div>
      {attribution && showAttribution ? (
        <figcaption className="mt-1 pr-2 text-right text-xs text-ink/40">
          Photo by{" "}
          <a href={attribution.photographer_url} className="underline hover:text-accent">
            {attribution.photographer}
          </a>{" "}
          on {attribution.source === "unsplash" ? "Unsplash" : "Pexels"}
        </figcaption>
      ) : null}
    </figure>
  );
}
