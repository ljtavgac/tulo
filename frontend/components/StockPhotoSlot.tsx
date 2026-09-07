// Placeholder for an image that will be sourced by fetch_stock_images.py
// (Unsplash/Pexels) once that integration is wired up -- not a live image.
export default function StockPhotoSlot({
  query,
  aspect = "hero",
  className = "",
}: {
  query: string;
  aspect?: "hero" | "thumbnail";
  className?: string;
}) {
  const aspectClass = aspect === "hero" ? "aspect-[16/9]" : "aspect-square";
  return (
    <div
      className={`flex ${aspectClass} flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-ink/20 bg-ink/5 text-center text-ink/50 ${className}`}
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
