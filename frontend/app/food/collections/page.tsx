import type { Metadata } from "next";
import Link from "next/link";
import { listPages } from "@/lib/api";
import { absoluteUrl, buildBreadcrumbList, pagePath, SITE_NAME } from "@/lib/seo";
import { sectionForTemplate } from "@/lib/taxonomy";
import Breadcrumbs from "@/components/Breadcrumbs";
import JsonLd from "@/components/JsonLd";

const TITLE = "Collections";
const DESCRIPTION = "Every curated recipe collection on Tulo -- organized by category, not an auto-generated tag archive.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/food/collections" },
  openGraph: { title: TITLE, description: DESCRIPTION, url: "/food/collections" },
};

export default async function CollectionsIndexPage() {
  const section = sectionForTemplate("category_roundup")!;
  const pages = await listPages("category_roundup");

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
      <h1 className="mt-4 text-3xl font-bold">Collections</h1>
      <p className="mt-3 max-w-2xl text-ink/70">
        Here&apos;s what&apos;s live right now -- new batches publish regularly, so this list keeps growing.
      </p>

      <ul className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {pages.map((page) => (
          <li key={page.slug}>
            <Link
              href={pagePath(page.template_type, page.slug)}
              className="block rounded-lg border border-ink/10 p-4 text-sm font-semibold hover:border-accent hover:text-accent"
            >
              {page.title}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
