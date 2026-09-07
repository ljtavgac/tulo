import { NextRequest, NextResponse } from "next/server";

// Backs the header search box's autocomplete dropdown. Proxies to the
// backend's existing /pages?q= search (same one /food/search uses) rather
// than adding a second search implementation, and trims to a handful of
// results since a dropdown -- unlike the full results page -- only has
// room to show a few.
const API_URL = process.env.API_URL || "http://localhost:8000";
const SUGGESTION_LIMIT = 6;

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get("q")?.trim();
  if (!q) {
    return NextResponse.json([]);
  }

  const url = new URL(`${API_URL}/pages`);
  url.searchParams.set("q", q);

  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    return NextResponse.json({ error: "Failed to search pages" }, { status: 502 });
  }

  const results = await res.json();
  return NextResponse.json(results.slice(0, SUGGESTION_LIMIT));
}
