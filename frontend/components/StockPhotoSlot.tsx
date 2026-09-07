import Image from "next/image";
import type { ImageAttribution } from "@/lib/types";

// Renders a real photo (sourced by backend/app/fetch_stock_images.py via
// Unsplash/Pexels) with required attribution once one exists for this
// page; falls back to a labeled placeholder box otherwise. Nothing about
// call sites needs to change based on which state a given page is in.
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
  const aspectClass = aspect === "hero" ? "aspect-[16/9]" : "aspect-square";

  if (imageUrl) {
    return (
      <figure className={className}>
        <div className={`relative ${aspectClass} overflow-hidden rounded-lg bg-ink/5`}>
          <Image src={imageUrl} alt={query} fill sizes="(min-width: 1024px) 640px, 100vw" className="object-cover" />
        </div>
        {attribution ? (
          <figcaption className="mt-1 text-right text-xs text-ink/40">
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

  return (
    <div
      className={`flex ${aspectClass} flex-col items-center justify-center gap-1 rounded-card border-2 border-dashed border-ink/20 bg-ink/5 text-center text-ink/50 ${className}`}
    >
      <span aria-hidden className="text-2xl">
        📷
      </span>
      <span className="px-3 text-xs">
        Stock photo slot — &ldquo;{query}&rdquo;
      </span>
    </div>
  );
}
