import type { Metadata } from "next";
import Link from "next/link";
import { getPage, listPages } from "@/lib/api";
import type { HomepageContent } from "@/lib/types";
import JsonLd from "@/components/JsonLd";
import PageTile from "@/components/PageTile";
import Carousel from "@/components/Carousel";
import { SITE_NAME, SITE_URL, pagePath } from "@/lib/seo";
import { sectionForTemplate, TOOL_PAGES } from "@/lib/taxonomy";

export async function generateMetadata(): Promise<Metadata> {
  const page = await getPage<HomepageContent>("homepage");
  const description = page?.content.meta_description;

  return {
    title: { absolute: SITE_NAME },
    description,
    alternates: { canonical: "/food" },
    openGraph: { title: SITE_NAME, description, url: "/food" },
  };
}

// One carousel per content template type, in the order they should appear.
const HOMEPAGE_SECTIONS = [
  "recipe_or_dish",
  "ingredient_hub",
  "howto_technique",
  "category_roundup",
  "definition",
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

  const sectionPages = await Promise.all(HOMEPAGE_SECTIONS.map((templateType) => listPages(templateType)));

  return (
    <main>
      {/* No visible hero copy or CTAs -- the recipes/ingredients/tools
          content below is the point, visible the moment the page loads.
          This heading is for accessibility/SEO only. */}
      <h1 className="sr-only">{SITE_NAME} -- recipes, ingredient guides, and kitchen tools</h1>
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

      {HOMEPAGE_SECTIONS.map((templateType, i) => {
        const pages = sectionPages[i];
        if (pages.length === 0) return null;
        const section = sectionForTemplate(templateType)!;

        return (
          <Carousel key={templateType} title={section.label} seeAllHref={section.hasIndex ? section.path : undefined}>
            {pages.map((p) => (
              <div key={p.slug} className="w-40 shrink-0 snap-start sm:w-48">
                <PageTile
                  href={pagePath(p.template_type, p.slug)}
                  title={p.title}
                  imageQuery={p.hero_image_query ?? p.title}
                  imageUrl={p.image_url}
                  imageAttribution={p.image_attribution}
                />
              </div>
            ))}
          </Carousel>
        );
      })}

      <Carousel title="Tools" seeAllHref="/food/tools">
        {TOOL_PAGES.map((tool) => (
          <Link
            key={tool.slug}
            href={pagePath("tool_page", tool.slug)}
            className="block w-40 shrink-0 snap-start rounded-card border border-ink/10 p-4 text-sm font-semibold hover:border-accent hover:text-accent sm:w-48"
          >
            {tool.title}
          </Link>
        ))}
      </Carousel>
    </main>
  );
}
