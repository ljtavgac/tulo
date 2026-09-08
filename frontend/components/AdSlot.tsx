// No ad network wired up yet (account/network TBD, see "Ad Unit
// Recommendations" in PAGE_TEMPLATES.md) -- renders nothing rather than a
// labeled gray placeholder box, since a visible "Ad unit (in-content)"
// dashed box reads as an obviously unfinished part of the page to a real
// visitor (and to anyone reviewing the site, e.g. for ad-network
// approval), not as a subtle empty slot. Positions are still reserved per
// the placement spec (two in-content slots, a desktop-only sticky sidebar
// slot, an in-feed slot blended into roundup grids) -- this component is
// just the one place all of them render through, so wiring in a real
// network later (an <ins class="adsbygoogle"> element, sized per variant
// the same way this placeholder was) only needs to happen here.
type Variant = "in-content" | "sidebar" | "in-feed";

export default function AdSlot({ variant: _variant }: { variant: Variant }) {
  return null;
}
