"use client";

import { useEffect, useRef } from "react";

// Real AdSense ad units, per the placement spec (two in-content slots, a
// desktop-only sticky sidebar slot, an in-feed slot blended into roundup
// grids -- see "Ad Unit Recommendations" in PAGE_TEMPLATES.md). Each
// variant needs its own ad unit created in the AdSense dashboard first
// (Ads > By ad unit > ... ) -- there's no way to generate a real slot ID
// or in-feed layout key from code, they're assigned by Google per unit.
// Until NEXT_PUBLIC_ADSENSE_SLOT_* is set for a variant, this renders
// nothing (same "inert without configuration" pattern as
// ADMIN_TASK_TOKEN/REVALIDATION_TOKEN elsewhere in this codebase) rather
// than a broken or blank ad box -- so it's safe to ship ahead of having
// every slot ID in hand, and each variant lights up independently the
// moment its own env var is set (Vercel env vars, then a redeploy: these
// need NEXT_PUBLIC_ so Next.js inlines them into the client bundle at
// build time, not just makes them available at request time).
type Variant = "in-content" | "sidebar" | "in-feed";

const ADSENSE_PUBLISHER_ID = "ca-pub-3064163087707472";

const AD_SLOTS: Record<Variant, string | undefined> = {
  "in-content": process.env.NEXT_PUBLIC_ADSENSE_SLOT_IN_CONTENT,
  sidebar: process.env.NEXT_PUBLIC_ADSENSE_SLOT_SIDEBAR,
  "in-feed": process.env.NEXT_PUBLIC_ADSENSE_SLOT_IN_FEED,
};

// In-feed units are a distinct AdSense ad format (for blending into a
// grid/list rather than sitting in a content column) and, unlike a normal
// display unit, come with a second Google-assigned value -- the layout
// key -- that has to be copied from that specific unit's own generated
// code snippet. There's no default that works generically across accounts.
const IN_FEED_LAYOUT_KEY = process.env.NEXT_PUBLIC_ADSENSE_IN_FEED_LAYOUT_KEY;

declare global {
  interface Window {
    adsbygoogle?: unknown[];
  }
}

export default function AdSlot({ variant }: { variant: Variant }) {
  const slot = AD_SLOTS[variant];
  const insRef = useRef<HTMLModElement>(null);

  // adsbygoogle.js (loaded once, site-wide, in layout.tsx) scans the DOM
  // for <ins class="adsbygoogle"> elements on its own initial load, but
  // Next.js's client-side navigation (next/link) never triggers a full
  // page reload -- so an <ins> that first appears on, say, the second
  // recipe page a visitor navigates to would never get picked up without
  // this. Pushing to window.adsbygoogle (initializing it as a plain array
  // if the library hasn't taken it over yet) is Google's own documented
  // pattern for exactly this "ad content inserted after the initial page
  // load" case -- the library drains any queued pushes once it's ready,
  // so the ordering between this effect and the script finishing its own
  // load is never a race to worry about.
  useEffect(() => {
    if (!slot) return;
    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch {
      // Expected pre-approval (AdSense hasn't reviewed the site yet) and
      // with any ad blocker -- never worth breaking the page over.
    }
  }, [slot]);

  if (!slot) return null;

  if (variant === "in-feed") {
    if (!IN_FEED_LAYOUT_KEY) return null;
    return (
      <ins
        ref={insRef}
        className="adsbygoogle"
        style={{ display: "block" }}
        data-ad-format="fluid"
        data-ad-layout-key={IN_FEED_LAYOUT_KEY}
        data-ad-client={ADSENSE_PUBLISHER_ID}
        data-ad-slot={slot}
      />
    );
  }

  return (
    <ins
      ref={insRef}
      className="adsbygoogle"
      style={{ display: "block" }}
      data-ad-client={ADSENSE_PUBLISHER_ID}
      data-ad-slot={slot}
      data-ad-format="auto"
      data-full-width-responsive="true"
    />
  );
}
