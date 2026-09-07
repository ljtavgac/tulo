import type { PageRecord, PageSummary } from "./types";

// Server-side base URL for the backend API. Set this to your deployed
// backend's HTTPS URL in production (see the root README for details).
const API_URL = process.env.API_URL || "http://localhost:8000";

// One hour: content here is generated ahead of time (not live-edited), so
// there's no need for anything shorter -- new batches trigger a fresh
// deploy anyway, which busts this automatically.
const REVALIDATE_SECONDS = 3600;

export async function getPage<T = Record<string, unknown>>(
  slug: string
): Promise<PageRecord<T> | null> {
  const res = await fetch(`${API_URL}/pages/${slug}`, {
    next: { revalidate: REVALIDATE_SECONDS },
  });
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
  const res = await fetch(url, { next: { revalidate: REVALIDATE_SECONDS } });
  if (!res.ok) throw new Error(`Failed to list pages: ${res.status}`);
  return res.json();
}

// Unlike listPages(), not cached -- a search is a one-off, per-query
// request, not content that benefits from being reused across visitors.
export async function searchPages(q: string): Promise<PageSummary[]> {
  const url = new URL(`${API_URL}/pages`);
  url.searchParams.set("q", q);
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to search pages: ${res.status}`);
  return res.json();
}
