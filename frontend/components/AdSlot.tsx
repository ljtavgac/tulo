// Placeholder ad unit. No network wired up -- account/network TBD (see
// "Ad Unit Recommendations" in PAGE_TEMPLATES.md). Positioned per the
// placement rules from that spec: two in-content slots, a desktop-only
// sticky sidebar slot, and an in-feed slot blended into roundup grids.
const LABELS: Record<Variant, string> = {
  "in-content": "Ad unit (in-content)",
  sidebar: "Ad unit (sticky sidebar, desktop only)",
  "in-feed": "Ad unit (in-feed)",
};

type Variant = "in-content" | "sidebar" | "in-feed";

export default function AdSlot({ variant }: { variant: Variant }) {
  const sizeClass =
    variant === "sidebar" ? "h-64 w-full" : variant === "in-feed" ? "h-40" : "h-24";
  const visibilityClass = variant === "sidebar" ? "hidden lg:flex" : "flex";

  return (
    <div
      className={`${visibilityClass} ${sizeClass} items-center justify-center rounded border border-dashed border-ink/15 bg-ink/[0.03] text-xs text-ink/40`}
    >
      {LABELS[variant]}
    </div>
  );
}
