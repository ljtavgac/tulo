import type { Metadata } from "next";
import type { PageRecord } from "./types";

// tulo.io is the intended production domain, not yet connected in Vercel as
// of this writing -- see root README. Falling back straight to localhost
// whenever NEXT_PUBLIC_SITE_URL isn't set meant every canonical URL,
// og:url, and sitemap entry silently pointed at http://localhost:3000 in
// production too, since nothing had ever set that env var on Vercel.
// VERCEL_PROJECT_PRODUCTION_URL is set automatically by Vercel on every
// build to whatever domain is currently assigned as the project's
// production domain (Vercel's own *.vercel.app one today, tulo.io once
// that's connected and marked primary -- no code change needed when that
// happens, just a redeploy) -- so this only actually falls back to
// localhost in local dev, where neither env var is set. Set
// NEXT_PUBLIC_SITE_URL explicitly to override this (e.g. to force a
// specific domain, or so a preview deployment still canonicalizes to the
// real production URL instead of self-canonicalizing to its own preview
// URL and risking duplicate-content indexing).
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ||
  (process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : "") ||
  "http://localhost:3000"
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

// Every route lives under /food/ -- the site's root namespace is reserved
// for future unrelated verticals (see lib/taxonomy.ts). This is the one
// place that prefix is defined; everything else (nav, breadcrumbs,
// sitemap, canonical URLs) composes through this function.
export function pagePath(templateType: string, slug: string): string {
  if (templateType === "homepage") return "/food";
  // static_page (About, Contact, ...) lives at the site root, not under
  // /food/ -- these are hand-coded routes (frontend/app/about,
  // frontend/app/contact), not content-driven [slug] templates, and their
  // Page record exists only so they can pull a real photo through the
  // usual fetch_images() pipeline (see seed_templates.py). The slug is
  // already the real route.
  if (templateType === "static_page") return `/${slug}`;
  const prefix = TEMPLATE_ROUTES[templateType];
  return prefix ? `/food/${prefix}/${slug}` : `/food/${slug}`;
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
      return `${title} - ingredients, instructions, and a live serving-size scaler. No story to scroll past.`;
    case "ingredient_hub":
      return `${title}: what it is, the best substitutes, storage tips, and how to use it.`;
    case "howto_technique":
      return `${title}, clear numbered steps and the common mistakes to avoid.`;
    case "definition":
      return `${title.replace(/^What Is /i, "").replace(/\?.*$/, "")} explained simply, with how it's used and what to substitute.`;
    case "comparison":
      return `${title}, a clear side-by-side comparison so you know which one to use.`;
    case "substitute":
      return `${title}, ranked, with exact ratios for each option.`;
    case "category_roundup":
      return `${title}, curated and organized, not an auto-generated tag archive.`;
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

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

// Builds a BreadcrumbList JSON-LD block from the trail a page passes in.
// The last item is assumed to be the current page and gets no href even if
// one is provided, matching how breadcrumbs are conventionally marked up.
export function buildBreadcrumbList(items: BreadcrumbItem[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: item.label,
      ...(item.href && i !== items.length - 1 ? { item: absoluteUrl(item.href) } : {}),
    })),
  };
}
