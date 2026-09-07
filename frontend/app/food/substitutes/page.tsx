import type { Metadata } from "next";
import { listPages } from "@/lib/api";
import { absoluteUrl, buildBreadcrumbList, pagePath, SITE_NAME } from "@/lib/seo";
import { sectionForTemplate } from "@/lib/taxonomy";
import Breadcrumbs from "@/components/Breadcrumbs";
import JsonLd from "@/components/JsonLd";
import PagedPageGrid from "@/components/PagedPageGrid";

const TITLE = "Substitutes";
const DESCRIPTION = "Every substitute guide on Tulo, ranked options with exact ratios.";
const PAGE_SIZE = 9;

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/food/substitutes" },
  openGraph: { title: TITLE, description: DESCRIPTION, url: "/food/substitutes" },
};

export default async function SubstitutesIndexPage() {
  const section = sectionForTemplate("substitute")!;
  const pages = await listPages("substitute", { limit: PAGE_SIZE, offset: 0 });

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
      <h1 className="mt-4 text-3xl font-bold">Substitutes</h1>
      <p className="mt-3 max-w-2xl text-ink/70">
        Ranked substitutes with exact ratios.
      </p>

      <PagedPageGrid initialPages={pages} templateType="substitute" pageSize={PAGE_SIZE} />
    </main>
  );
}
