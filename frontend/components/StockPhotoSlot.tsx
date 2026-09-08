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
}) {
  const [failed, setFailed] = useState(false);

  const aspectClass = aspect === "hero" ? "aspect-[16/9]" : "aspect-square";

  if (!imageUrl || failed) {
    if (!reserveSpace) return null;
    return <div className={`${aspectClass} rounded-lg bg-ink/5 ${className}`} />;
  }

  return (
    <figure className={className}>
      <div className={`relative ${aspectClass} overflow-hidden rounded-lg bg-ink/5`}>
        <Image
          src={imageUrl}
          alt={alt || query}
          fill
          unoptimized
          sizes="(min-width: 1024px) 640px, 100vw"
          className="object-cover"
          onError={() => setFailed(true)}
        />
      </div>
      {attribution ? (
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
