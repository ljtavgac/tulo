// Peak months and a display label for ingredients with a real,
// consumer-relevant season. Deliberately sparse: most of this site's
// ingredient hubs are pantry staples (cornstarch, bread flour, celtic
// salt) or dairy/cured/aged products (gruyère, feta, pecorino, crème
// fraîche, kielbasa, balsamic vinegar) that are produced and sold
// year-round with no season a reader would recognize or act on --
// inventing one for them would be padding, not information. Only add an
// entry here when the peak months are a real, checkable fact.
export const SEASONALITY: Record<string, { months: number[]; label: string }> = {
  // Fresh herb, peak spring through early summer in most of the US.
  chives: { months: [4, 5, 6, 7], label: "April–July" },
  // The traditional "only eat oysters in months with an R" guideline --
  // rooted in pre-refrigeration food safety and spawning-season quality,
  // still commonly used as a seasonal guide today.
  oysters: { months: [9, 10, 11, 12, 1, 2, 3, 4], label: "September–April" },
};

export function getSeasonality(slug: string): { months: number[]; label: string } | null {
  return SEASONALITY[slug] ?? null;
}
