import type { Metadata } from "next";
import { listPages } from "@/lib/api";
import { absoluteUrl, buildBreadcrumbList, pagePath, SITE_NAME } from "@/lib/seo";
import { sectionForTemplate } from "@/lib/taxonomy";
import Breadcrumbs from "@/components/Breadcrumbs";
import JsonLd from "@/components/JsonLd";
import PagedPageGrid from "@/components/PagedPageGrid";

const TITLE = "Definitions";
const DESCRIPTION = "Every definition page on Tulo -- quick, direct answers to \"what is X\" questions.";
const PAGE_SIZE = 9;

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/food/what-is" },
  openGraph: { title: TITLE, description: DESCRIPTION, url: "/food/what-is" },
};

export default async function DefinitionsIndexPage() {
  const section = sectionForTemplate("definition")!;
  const pages = await listPages("definition", { limit: PAGE_SIZE, offset: 0 });

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
      <h1 className="mt-4 text-3xl font-bold">Definitions</h1>
      <p className="mt-3 max-w-2xl text-ink/70">
        Here&apos;s what&apos;s live right now -- new batches publish regularly, so this list keeps growing.
      </p>

      <PagedPageGrid initialPages={pages} templateType="definition" pageSize={PAGE_SIZE} />
    </main>
  );
}
