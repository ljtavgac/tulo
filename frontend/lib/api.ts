import type { PageRecord, PageSummary } from "./types";

// Server-side base URL for the backend API. Set this to your deployed
// backend's HTTPS URL in production (see the root README for details).
const API_URL = process.env.API_URL || "http://localhost:8000";

// This used to cache for 120 seconds (next: { revalidate: 120 }) rather
// than fetch fresh every time, on the theory that a short TTL would still
// self-heal any staleness within a few minutes even if a deploy or
// /api/revalidate call didn't bust it -- see backend/app/main.py's
// _revalidate_frontend. In practice that didn't hold: specific pages were
// confirmed, directly against the backend's own /pages/<slug> response, to
// have fully correct and current content while the deployed frontend kept
// serving stale HTML for those same pages across multiple days and
// several backend deploys -- proving the staleness was living in this
// cache layer, not the data. Rather than debug Vercel's Data Cache/ISR
// behavior blind (there's no way to inspect it directly), this fetches
// fresh on every request instead. At this site's current scale that's a
// negligible cost against the backend, and it makes an entire class of
// "the fix shipped but isn't showing up" bug impossible by construction.
export async function getPage<T = Record<string, unknown>>(
  slug: string
): Promise<PageRecord<T> | null> {
  const res = await fetch(`${API_URL}/pages/${slug}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch page "${slug}": ${res.status}`);
  return res.json();
}

export async function listPages(
  templateType?: string,
  options?: { limit?: number; offset?: number }
): Promise<PageSummary[]> {
  const url = new URL(`${API_URL}/pages`);
  if (templateType) url.searchParams.set("template_type", templateType);
  if (options?.limit != null) url.searchParams.set("limit", String(options.limit));
  if (options?.offset != null) url.searchParams.set("offset", String(options.offset));
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to list pages: ${res.status}`);
  return res.json();
}

// Same reasoning as getPage/listPages above -- always fetch fresh.
export async function searchPages(q: string): Promise<PageSummary[]> {
  const url = new URL(`${API_URL}/pages`);
  url.searchParams.set("q", q);
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to search pages: ${res.status}`);
  return res.json();
}
