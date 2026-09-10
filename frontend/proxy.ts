import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Belt-and-suspenders alongside robots.ts: robots.ts tells crawlers not to
// fetch staging at all, but this header blocks indexing even if something
// links to a staging URL directly (or a crawler ignores robots.txt). See
// robots.ts for why VERCEL_ENV is the right signal here.
const IS_PRODUCTION = process.env.VERCEL_ENV === "production";

export function proxy(request: NextRequest) {
  if (IS_PRODUCTION) {
    return NextResponse.next();
  }
  const response = NextResponse.next();
  response.headers.set("X-Robots-Tag", "noindex, nofollow");
  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
