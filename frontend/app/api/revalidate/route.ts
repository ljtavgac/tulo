import { timingSafeEqual } from "node:crypto";
import { revalidatePath } from "next/cache";
import { NextRequest, NextResponse } from "next/server";

// Every page fetch is cached for an hour (see lib/api.ts), which is fine
// for content that only changes via a scheduled batch -- but there's no
// other way to force a page to pick up a backend change sooner (e.g. after
// backfilling stock photos, or fixing a content bug). This is that escape
// hatch. Gated behind REVALIDATION_TOKEN so it isn't a public endpoint
// anyone can hit to force-refresh the whole site on a whim -- if that env
// var isn't set, this always 404s, matching the same "inert without
// configuration" pattern used for the backend's /admin/fetch-images.
const REVALIDATION_TOKEN = process.env.REVALIDATION_TOKEN;

function isValidToken(token: string | null): boolean {
  if (!REVALIDATION_TOKEN || !token) return false;
  const expected = Buffer.from(REVALIDATION_TOKEN);
  const actual = Buffer.from(token);
  return expected.length === actual.length && timingSafeEqual(expected, actual);
}

export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token");
  if (!isValidToken(token)) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  // Revalidates every cached page on the site. Blunt, but there are only a
  // handful of pages today and this is meant for occasional manual use --
  // a targeted `path` param can be added later if that ever stops being
  // true.
  revalidatePath("/", "layout");

  return NextResponse.json({ revalidated: true, now: Date.now() });
}
