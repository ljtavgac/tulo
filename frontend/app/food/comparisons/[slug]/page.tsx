import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPage } from "@/lib/api";
import type { ComparisonContent } from "@/lib/types";
import { buildBreadcrumbList, buildPageMetadata, pagePath } from "@/lib/seo";
import { sectionForTemplate } from "@/lib/taxonomy";
import JsonLd from "@/components/JsonLd";
import Breadcrumbs from "@/components/Breadcrumbs";
import FaqSection from "@/components/FaqSection";
import StockPhotoSlot from "@/components/StockPhotoSlot";
import AdSlot from "@/components/AdSlot";
import LinkifiedText from "@/components/LinkifiedText";
import Link from "next/link";
import { getLinkTerms } from "@/lib/linkTerms";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const page = await getPage<ComparisonContent>(slug);
  if (!page || page.template_type !== "comparison") return {};
  return buildPageMetadata(page);
}

export default async function ComparisonPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const page = await getPage<ComparisonContent>(slug);
  if (!page || page.template_type !== "comparison") notFound();

  const { content } = page;

  const section = sectionForTemplate(page.template_type)!;
  const breadcrumbItems = [
    { label: "Home", href: "/" },
    { label: section.label, href: section.hasIndex ? section.path : undefined },
    { label: page.title },
  ];
  const linkTerms = await getLinkTerms();

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <Breadcrumbs items={breadcrumbItems} />
      <JsonLd data={buildBreadcrumbList(breadcrumbItems)} />
      <h1 className="mt-4 text-3xl font-bold">{page.title}</h1>
      <StockPhotoSlot
        query={content.hero_image_query ?? `${content.item_a_name} vs ${content.item_b_name}`}
        alt={content.image_alt}
        imageUrl={content.image_url}
        attribution={content.image_attribution}
        className="mt-4"
        priority
      />

      <div className="mt-6 overflow-x-auto">
        <table className="w-full border-collapse overflow-hidden rounded-lg border border-ink/10 text-sm">
          <thead>
            <tr className="bg-ink/5 text-left">
              <th className="p-3 font-semibold"> </th>
              <th className="p-3 font-semibold">{content.item_a_name}</th>
              <th className="p-3 font-semibold">{content.item_b_name}</th>
            </tr>
          </thead>
          <tbody>
            {content.comparison_table.map((row) => (
              <tr key={row.attribute} className="border-t border-ink/10">
                <td className="p-3 font-medium text-ink/60">{row.attribute}</td>
                <td className="p-3">{row.item_a}</td>
                <td className="p-3">{row.item_b}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-6 rounded-lg border-l-4 border-accent bg-ink/5 p-4">
        <p className="text-sm font-semibold uppercase tracking-wide text-accent">Verdict</p>
        <p className="mt-1 text-ink/80">{content.verdict}</p>
      </div>

      <AdSlot variant="in-content" />

      {content.sections.map((section) => (
        <section key={section.heading} className="mt-8">
          <h2 className="text-xl font-bold">{section.heading}</h2>
          <p className="mt-2 text-ink/80">
            <LinkifiedText text={section.body} terms={linkTerms} />
          </p>
        </section>
      ))}

      {content.item_a_link || content.item_b_link ? (
        <div className="mt-8 flex flex-wrap gap-3">
          {content.item_a_link ? (
            <Link
              href={pagePath("ingredient_hub", content.item_a_link.slug)}
              className="rounded-full border border-ink/20 px-4 py-2 text-sm font-medium hover:border-accent hover:text-accent"
            >
              More on {content.item_a_link.title}
            </Link>
          ) : null}
          {content.item_b_link ? (
            <Link
              href={pagePath("ingredient_hub", content.item_b_link.slug)}
              className="rounded-full border border-ink/20 px-4 py-2 text-sm font-medium hover:border-accent hover:text-accent"
            >
              More on {content.item_b_link.title}
            </Link>
          ) : null}
        </div>
      ) : null}

      <FaqSection faqs={content.faqs} />
    </main>
  );
}
