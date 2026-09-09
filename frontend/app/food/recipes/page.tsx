import type { Metadata } from "next";
import { listPages } from "@/lib/api";
import { absoluteUrl, buildBreadcrumbList, pagePath, SITE_NAME } from "@/lib/seo";
import { sectionForTemplate } from "@/lib/taxonomy";
import Breadcrumbs from "@/components/Breadcrumbs";
import JsonLd from "@/components/JsonLd";
import PagedPageGrid from "@/components/PagedPageGrid";

const TITLE = "Recipes";
const DESCRIPTION = "Every recipe on Tulo, ingredients and instructions up front, no story to scroll past.";
// Must be a multiple of both the mobile (2-col) and desktop (3-col) grid
// widths from PagedPageGrid.tsx, or "Load more" leaves a partial last row on
// whichever breakpoint 9 (divisible by 3 but not 2) used to break on mobile.
const PAGE_SIZE = 12;

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/food/recipes" },
  openGraph: { title: TITLE, description: DESCRIPTION, url: "/food/recipes" },
};

export default async function RecipesIndexPage() {
  const section = sectionForTemplate("recipe_or_dish")!;
  const pages = await listPages("recipe_or_dish", { limit: PAGE_SIZE, offset: 0 });

  const breadcrumbItems = [
    { label: "Home", href: "/" },
    { label: "Food", href: "/food" },
    { label: section.label },
  ];

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <Breadcrumbs items={breadcrumbItems} />
      <JsonLd data={buildBreadcrumbList(breadcrumbItems)} />
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "CollectionPage",
          name: `${TITLE} | ${SITE_NAME}`,
          url: absoluteUrl(section.path),
          mainEntity: {
            "@type": "ItemList",
            itemListElement: pages.map((page, i) => ({
              "@type": "ListItem",
              position: i + 1,
              name: page.title,
              url: absoluteUrl(pagePath(page.template_type, page.slug)),
            })),
          },
        }}
      />
      <h1 className="mt-4 text-3xl font-bold">Recipes</h1>
      <p className="mt-3 max-w-2xl text-ink/70">
        Full recipes with real ingredient amounts and clear steps.
      </p>

      <PagedPageGrid initialPages={pages} templateType="recipe_or_dish" pageSize={PAGE_SIZE} />
    </main>
  );
}
