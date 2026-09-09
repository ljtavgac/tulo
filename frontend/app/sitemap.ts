import type { MetadataRoute } from "next";
import { listPages } from "@/lib/api";
import { SITE_URL, pagePath } from "@/lib/seo";

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
// static_page (About, Contact) is excluded on purpose -- low-value,
// low-change utility pages that don't need search visibility, by
// deliberate choice rather than oversight. Privacy has no Page record at
// all (a pure static route, see app/privacy/page.tsx) so it was already
// excluded for free; this just makes About/Contact consistent with it.
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const pages = (await listPages()).filter((page) => page.template_type !== "static_page");

  return pages.map((page) => ({
    url: `${SITE_URL}${pagePath(page.template_type, page.slug)}`,
    changeFrequency: CHANGE_FREQUENCY[page.template_type] ?? "monthly",
    priority: PRIORITY[page.template_type] ?? 0.5,
  }));
}
