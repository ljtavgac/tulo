import type { Metadata } from "next";
import Link from "next/link";
import { Fragment } from "react";
import { getPage, listPages } from "@/lib/api";
import type { HomepageContent } from "@/lib/types";
import JsonLd from "@/components/JsonLd";
import PageTile from "@/components/PageTile";
import Carousel from "@/components/Carousel";
import ToolIcon from "@/components/ToolIcon";
import AdSlot from "@/components/AdSlot";
import { SITE_NAME, SITE_URL, pagePath } from "@/lib/seo";
import { sectionForTemplate, TOOL_PAGES } from "@/lib/taxonomy";

// Indices (into HOMEPAGE_SECTIONS) after which an in-content ad renders --
// matches the "two in-content slots" placement used on Recipe pages,
// spaced out between carousels instead of mid-article.
const AD_AFTER_SECTION_INDEX = new Set([1, 3, 5]);

// Hardcoded rather than pulled from the backend's homepage Page row (as
// description used to be) -- both are brand-level SEO copy, not content
// that changes with what's in the carousels, so they belong with the
// title below as fixed literals, not a live lookup.
const DESCRIPTION =
  "Recipes that scale to your serving size, plus ingredient guides, how-to techniques, substitutes, and free kitchen tools.";

export async function generateMetadata(): Promise<Metadata> {
  return {
    // Brand-level, not food-specific -- this is now the permanent
    // multi-vertical root (see the / -> /food removal this replaced), and
    // a food-specific title would need to be undone the moment a second
    // vertical launches. The tagline lives here rather than in SITE_NAME
    // itself since every other page's title still wants the bare "Tulo"
    // (via layout.tsx's title.template), not this longer form.
    title: { absolute: "Tulo — Recipes, Ingredient Guides & Kitchen Tools" },
    description: DESCRIPTION,
    alternates: { canonical: "/" },
    openGraph: { title: SITE_NAME, description: DESCRIPTION, url: "/" },
  };
}

// A carousel is a horizontally-scrolling teaser, not a full listing -- the
// section index pages (linked via "See all") already exist for that. This
// used to fetch every page of a section's template_type with no limit at
// all (up to ~950 rows for ingredient_hub), rendering every one of them
// into the carousel's DOM on every single homepage view -- one of the
// heaviest single page loads on the whole site, on what's likely its most
// visited page. Newest-first ordering (already the list endpoint's
// default) means a bounded fetch still surfaces genuinely new content.
const CAROUSEL_SIZE = 20;

// One carousel per content template type, in the order they should appear.
const HOMEPAGE_SECTIONS = [
  "recipe_or_dish",
  "ingredient_hub",
  "howto_technique",
  "category_roundup",
  "definition",
  "comparison",
  "substitute",
];

export default async function HomePage() {
  const page = await getPage<HomepageContent>("homepage");

  if (!page) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-16 text-center">
        <p>Could not load homepage content from the backend.</p>
      </main>
    );
  }

  const sectionPages = await Promise.all(
    HOMEPAGE_SECTIONS.map((templateType) => listPages(templateType, { limit: CAROUSEL_SIZE, offset: 0 }))
  );

  return (
    <main>
      {/* This heading is for accessibility/SEO only -- kept visually
          hidden since the recipes/ingredients/tools content below is
          still the point, visible the moment the page loads. The intro
          paragraph right after it IS visible, unlike before; it exists
          for the same reason the heading does (a crawler and a
          screen-reader user both need to be told what this site is
          before the carousels start), just as prose a sighted visitor
          can also read. */}
      <h1 className="sr-only">{SITE_NAME} - recipes, ingredient guides, and kitchen tools</h1>
      <p className="mx-auto max-w-3xl px-4 pt-8 text-center text-ink/80">
        Tulo is a cooking reference built around the recipe you already have in mind, not a
        blog to scroll past first. Every recipe adjusts live to your serving size and
        measurement units, with ingredient guides, step-by-step techniques, and substitute
        comparisons linked right from the instructions.
      </p>
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "WebSite",
          name: SITE_NAME,
          url: SITE_URL,
          potentialAction: {
            "@type": "SearchAction",
            target: `${SITE_URL}/food/search?q={search_term_string}`,
            "query-input": "required name=search_term_string",
          },
        }}
      />
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "Organization",
          name: SITE_NAME,
          url: SITE_URL,
          logo: `${SITE_URL}/brand/tulo-light.png`,
          // No sameAs: Tulo has no real, live social profiles anywhere in
          // this codebase today (checked -- none are linked from the
          // footer, contact page, or anywhere else). Adding one here
          // would be inventing a source of truth that doesn't exist;
          // add sameAs URLs once real profiles exist to link.
        }}
      />

      {HOMEPAGE_SECTIONS.map((templateType, i) => {
        const pages = sectionPages[i];
        if (pages.length === 0) return null;
        const section = sectionForTemplate(templateType)!;

        return (
          <Fragment key={templateType}>
            <Carousel title={section.label} seeAllHref={section.hasIndex ? section.path : undefined}>
              {pages.map((p, j) => (
                <div key={p.slug} className="w-40 shrink-0 snap-start sm:w-48">
                  <PageTile
                    href={pagePath(p.template_type, p.slug)}
                    title={p.title}
                    imageQuery={p.hero_image_query ?? p.title}
                    imageAlt={p.image_alt}
                    imageUrl={p.image_url}
                    imageAttribution={p.image_attribution}
                    // Only the very first tile of the very first carousel
                    // row sits above the fold -- see StockPhotoSlot's
                    // `priority` doc for why lazy-loading that one specifically
                    // hurts LCP.
                    priority={i === 0 && j === 0}
                  />
                </div>
              ))}
            </Carousel>
            {AD_AFTER_SECTION_INDEX.has(i) ? (
              <div className="mx-auto max-w-6xl px-4">
                <AdSlot variant="in-content" />
              </div>
            ) : null}
          </Fragment>
        );
      })}

      <Carousel title="Tools" seeAllHref="/food/tools">
        {TOOL_PAGES.map((tool) => (
          <Link
            key={tool.slug}
            href={pagePath("tool_page", tool.slug)}
            className="flex w-40 shrink-0 snap-start flex-col gap-3 rounded-card bg-cream p-4 shadow-card transition-shadow hover:shadow-lg sm:w-48"
          >
            <ToolIcon icon={tool.icon} className="h-8 w-8 text-accent" />
            <span className="line-clamp-2 min-h-10 text-sm font-bold">{tool.title}</span>
          </Link>
        ))}
      </Carousel>
    </main>
  );
}
