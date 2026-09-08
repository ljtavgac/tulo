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
export default function StockPhotoSlot({
  query,
  imageUrl,
  attribution,
  aspect = "hero",
  className = "",
}: {
  query: string;
  imageUrl?: string;
  attribution?: ImageAttribution;
  aspect?: "hero" | "thumbnail";
  className?: string;
}) {
  const [failed, setFailed] = useState(false);

  if (!imageUrl || failed) return null;

  const aspectClass = aspect === "hero" ? "aspect-[16/9]" : "aspect-square";

  return (
    <figure className={className}>
      <div className={`relative ${aspectClass} overflow-hidden rounded-lg bg-ink/5`}>
        <Image
          src={imageUrl}
          alt={query}
          fill
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
