import { NextRequest, NextResponse } from "next/server";

// Backs the "Load more" button on section index pages. Those pages start
// as server components (so the first page of results is part of the
// initial HTML, for SEO), but "load more" runs client-side -- and a client
// component can't call the backend directly, since API_URL is a
// server-only env var (see lib/api.ts) -- so this proxies to backend
// GET /pages with the same template_type/limit/offset params.
const API_URL = process.env.API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  const templateType = request.nextUrl.searchParams.get("template_type");
  const limit = request.nextUrl.searchParams.get("limit");
  const offset = request.nextUrl.searchParams.get("offset");

  const url = new URL(`${API_URL}/pages`);
  if (templateType) url.searchParams.set("template_type", templateType);
  if (limit) url.searchParams.set("limit", limit);
  if (offset) url.searchParams.set("offset", offset);

  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    return NextResponse.json({ error: "Failed to list pages" }, { status: 502 });
  }

  return NextResponse.json(await res.json());
}
