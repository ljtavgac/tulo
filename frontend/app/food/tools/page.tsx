import type { Metadata } from "next";
import Link from "next/link";
import { absoluteUrl, buildBreadcrumbList, pagePath, SITE_NAME } from "@/lib/seo";
import { sectionForTemplate, TOOL_PAGES } from "@/lib/taxonomy";
import Breadcrumbs from "@/components/Breadcrumbs";
import JsonLd from "@/components/JsonLd";
import ToolIcon from "@/components/ToolIcon";

const TITLE = "Kitchen Tools";
const DESCRIPTION = "Free kitchen tools on Tulo -- conversion calculator, recipe generator, and a time & temperature guide.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/food/tools" },
  openGraph: { title: TITLE, description: DESCRIPTION, url: "/food/tools" },
};

export default function ToolsIndexPage() {
  const section = sectionForTemplate("tool_page")!;

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
            itemListElement: TOOL_PAGES.map((tool, i) => ({
              "@type": "ListItem",
              position: i + 1,
              name: tool.title,
              url: absoluteUrl(pagePath("tool_page", tool.slug)),
            })),
          },
        }}
      />
      <h1 className="mt-4 text-3xl font-bold">Kitchen Tools</h1>
      <p className="mt-3 max-w-2xl text-ink/70">Free tools, no sign-up required.</p>

      <ul className="mt-6 grid gap-4 sm:grid-cols-3">
        {TOOL_PAGES.map((tool) => (
          <li key={tool.slug}>
            <Link
              href={pagePath("tool_page", tool.slug)}
              className="flex items-center gap-3 rounded-lg border border-ink/10 p-4 text-sm font-semibold hover:border-accent hover:text-accent"
            >
              <ToolIcon icon={tool.icon} className="h-8 w-8 shrink-0 text-accent" />
              {tool.title}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
