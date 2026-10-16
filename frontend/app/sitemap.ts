import type { MetadataRoute } from "next";
import { listPages } from "@/lib/api";
import { SITE_URL, pagePath } from "@/lib/seo";
import { FOOD_SECTIONS } from "@/lib/taxonomy";

const PRIORITY: Record<string, number> = {
  homepage: 1,
  recipe_or_dish: 0.8,
  category_roundup: 0.8,
  tool_page: 0.7,
  ingredient_hub: 0.6,
  howto_technique: 0.6,
  definition: 0.5,
  comparison: 0.5,
  substitute: 0.5,
};

const CHANGE_FREQUENCY: Record<string, MetadataRoute.Sitemap[number]["changeFrequency"]> = {
  homepage: "daily",
  recipe_or_dish: "weekly",
  category_roundup: "weekly",
  tool_page: "monthly",
};

// Dynamic by design: reads every page currently in the backend, so it
// automatically covers each week's new batch from CONTENT_QUEUE.csv
// without needing to touch this file again.
//
// static_page (Contact, ...) stays excluded on purpose -- low-value,
// low-change utility pages that don't need search visibility, by
// deliberate choice rather than oversight. The homepage, About, and
// Privacy are added explicitly below instead (see staticEntries) --
// confirmed missing or malformed live (2026-10-16): homepage was present
// but as `${SITE_URL}/`, a trailing slash the live canonical tag doesn't
// have (`https://tulo.io`, not `https://tulo.io/`), and About/Privacy
// weren't in the sitemap at all (About is a real static_page row, so it
// was caught by this same filter; Privacy has no Page record at all).
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const pages = (await listPages()).filter(
    (page) => page.template_type !== "static_page" && page.template_type !== "homepage"
  );

  // The homepage, About, and Privacy: three singular, hand-coded routes,
  // not data-driven template content, so they're listed explicitly here
  // rather than through the dynamic Page-row loop below. The homepage's
  // URL is SITE_URL with no path appended at all -- matching exactly what
  // the homepage's own canonical tag renders (alternates.canonical: "/"
  // resolved against metadataBase collapses to the bare origin, not
  // `${SITE_URL}/`) -- rather than reusing pagePath("homepage", slug),
  // which returns "/" and would reintroduce the same trailing-slash
  // mismatch this was added to fix.
  const staticEntries: MetadataRoute.Sitemap = [
    { url: SITE_URL, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/about`, changeFrequency: "yearly", priority: 0.3 },
    { url: `${SITE_URL}/privacy`, changeFrequency: "yearly", priority: 0.3 },
  ];

  // The 8 hub/section index pages (e.g. /food/recipes) are static routes
  // that list pages of a template type -- they're never a Page row
  // themselves, so the dynamic loop below can never produce a bare
  // /food/{section} entry for them. Added explicitly here, same
  // priority/changeFrequency as category_roundup: these are primary
  // discovery pages, not individual content.
  const hubEntries: MetadataRoute.Sitemap = FOOD_SECTIONS.filter((section) => section.hasIndex).map((section) => ({
    url: `${SITE_URL}${section.path}`,
    changeFrequency: "weekly",
    priority: 0.8,
  }));

  const pageEntries = pages.map((page) => ({
    url: `${SITE_URL}${pagePath(page.template_type, page.slug)}`,
    changeFrequency: CHANGE_FREQUENCY[page.template_type] ?? "monthly",
    priority: PRIORITY[page.template_type] ?? 0.5,
  }));

  return [...staticEntries, ...hubEntries, ...pageEntries];
}
