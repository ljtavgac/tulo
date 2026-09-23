import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

// VERCEL_ENV is set automatically on every Vercel deployment -- no config
// needed here -- to "production" only for the deployment aliased to the
// project's actual Production Domain; every other deployment (a branch's
// preview URL, or a custom domain like staging.tulo.io pointed at a
// non-production branch) gets "preview" or "development" instead. Used
// here rather than trusting Vercel's own default preview-deployment
// noindex behavior, which is real but undocumented for the custom-domain
// case specifically -- this way staging's exclusion from search doesn't
// depend on guessing at platform behavior we can't verify from here.
const IS_PRODUCTION = process.env.VERCEL_ENV === "production";

export default function robots(): MetadataRoute.Robots {
  if (!IS_PRODUCTION) {
    return { rules: { userAgent: "*", disallow: "/" } };
  }
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // ~1,100 Ingredient Hub pages each link to the Recipe Generator with
      // their own ingredient pre-filled (?ingredients=<name>), all
      // self-canonicalizing back to the clean tool URL -- correct, but not
      // worth Googlebot's crawl budget on this many near-duplicate URLs.
      // No trailing wildcard needed: robots.txt path values are prefix
      // matches by default, so this blocks every ?ingredients=... variant
      // without touching the clean /food/tools/recipe-generator URL itself.
      disallow: "/food/tools/recipe-generator?ingredients=",
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
