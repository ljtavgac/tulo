import { NextRequest, NextResponse } from "next/server";

// The client component behind the Recipe Generator can't reach the backend
// directly -- API_URL is a server-only env var (see lib/api.ts), not
// NEXT_PUBLIC_-prefixed -- so this proxies the request server-side to
// backend GET /recipes/match instead of duplicating that env var as a
// public one just for this one tool.
const API_URL = process.env.API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  const ingredients = request.nextUrl.searchParams.get("ingredients");
  if (!ingredients) {
    return NextResponse.json({ error: "Missing ingredients" }, { status: 400 });
  }

  const url = new URL(`${API_URL}/recipes/match`);
  url.searchParams.set("ingredients", ingredients);

  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    return NextResponse.json({ error: "Failed to match recipes" }, { status: 502 });
  }

  return NextResponse.json(await res.json());
}
