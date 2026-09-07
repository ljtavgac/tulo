import type { Metadata } from "next";
import type { PageRecord } from "./types";

// The production URL isn't finalized yet (no custom domain connected as of
// this writing -- see root README). Set NEXT_PUBLIC_SITE_URL once one is,
// so canonical URLs, the sitemap, and Open Graph tags point at the real
// domain instead of a Vercel preview URL.
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"
).replace(/\/$/, "");

export const SITE_NAME = "Tulo";

// Maps a page's template_type to its URL path segment. Single source of
// truth for routing -- used by generateMetadata's canonical URLs, the
// sitemap, and internal link-building alike.
export const TEMPLATE_ROUTES: Record<string, string> = {
  recipe_or_dish: "recipes",
  ingredient_hub: "ingredients",
  howto_technique: "how-to",
  definition: "what-is",
  comparison: "vs",
  substitute: "substitutes",
  category_roundup: "collections",
  tool_page: "tools",
};

export function pagePath(templateType: string, slug: string): string {
  if (templateType === "homepage") return "/";
  const prefix = TEMPLATE_ROUTES[templateType];
  return prefix ? `/${prefix}/${slug}` : `/${slug}`;
}

export function absoluteUrl(path: string): string {
  return `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

// Fallback description generator, for any future batch-generated page that
// doesn't include a hand-written meta_description. Keeps every page shipping
// *some* unique-ish description rather than falling back to the site-wide
// default (which would create duplicate <meta description> tags at scale).
export function fallbackDescription(templateType: string, title: string): string {
  switch (templateType) {
    case "recipe_or_dish":
      return `${title} -- ingredients, instructions, and a live serving-size scaler. No story to scroll past.`;
    case "ingredient_hub":
      return `${title}: what it is, the best substitutes, storage tips, and how to use it.`;
    case "howto_technique":
      return `${title} -- clear numbered steps and the common mistakes to avoid.`;
    case "definition":
      return `${title.replace(/^What Is /i, "").replace(/\?.*$/, "")} explained simply, with how it's used and what to substitute.`;
    case "comparison":
      return `${title} -- a clear side-by-side comparison so you know which one to use.`;
    case "substitute":
      return `${title}, ranked, with exact ratios for each option.`;
    case "category_roundup":
      return `${title}, curated and organized -- not an auto-generated tag archive.`;
    default:
      return `${title} | ${SITE_NAME}`;
  }
}

// Shared metadata builder for the 7 content-template pages -- title,
// description (hand-written if the content has one, else a sensible
// per-template fallback), canonical URL, and matching Open Graph tags.
export function buildPageMetadata(
  page: PageRecord<{ meta_description?: string }> | null
): Metadata {
  if (!page) return {};
  const description = page.content.meta_description || fallbackDescription(page.template_type, page.title);
  const path = pagePath(page.template_type, page.slug);

  return {
    title: page.title,
    description,
    alternates: { canonical: path },
    openGraph: { title: page.title, description, url: path, type: "article" },
  };
}

// Minutes -> ISO 8601 duration, for Recipe schema's prepTime/cookTime/totalTime.
export function minutesToIso8601(minutes: number): string {
  return `PT${minutes}M`;
}
