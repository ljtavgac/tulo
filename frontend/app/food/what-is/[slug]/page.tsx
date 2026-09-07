import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPage } from "@/lib/api";
import type { DefinitionContent } from "@/lib/types";
import StockPhotoSlot from "@/components/StockPhotoSlot";
import JsonLd from "@/components/JsonLd";
import Breadcrumbs from "@/components/Breadcrumbs";
import FaqSection from "@/components/FaqSection";
import RelatedLinks from "@/components/RelatedLinks";
import Link from "next/link";
import { buildBreadcrumbList, buildPageMetadata, pagePath } from "@/lib/seo";
import { sectionForTemplate } from "@/lib/taxonomy";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const page = await getPage<DefinitionContent>(slug);
  if (!page || page.template_type !== "definition") return {};
  return buildPageMetadata(page);
}

export default async function DefinitionPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const page = await getPage<DefinitionContent>(slug);
  if (!page || page.template_type !== "definition") notFound();

  const { content } = page;

  const section = sectionForTemplate(page.template_type)!;
  const breadcrumbItems = [
    { label: "Home", href: "/" },
    { label: "Food", href: "/food" },
    { label: section.label, href: section.hasIndex ? section.path : undefined },
    { label: page.title },
  ];

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <Breadcrumbs items={breadcrumbItems} />
      <JsonLd data={buildBreadcrumbList(breadcrumbItems)} />
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "DefinedTerm",
          name: page.title.replace(/^What Is /i, "").replace(/\?.*$/, ""),
          description: content.direct_answer,
        }}
      />
      <h1 className="mt-4 text-3xl font-bold">{page.title}</h1>

      {/* Direct answer up top, ahead of the hero image -- featured-snippet
          optimized, per the Definition template spec. */}
      <p className="mt-4 rounded-lg bg-ink/5 p-4 text-lg font-medium">{content.direct_answer}</p>

      <StockPhotoSlot
        query={content.hero_image_query}
        imageUrl={content.image_url}
        attribution={content.image_attribution}
        className="mt-4"
      />

      <h2 className="mt-8 text-xl font-bold">More detail</h2>
      <p className="mt-2 text-ink/80">{content.expanded_explanation}</p>

      <h2 className="mt-8 text-xl font-bold">Where it's used</h2>
      <p className="mt-2 text-ink/80">{content.usage_origin}</p>

      <h2 className="mt-8 text-xl font-bold">Substitutes</h2>
      <p className="mt-2 text-ink/80">{content.substitute_note}</p>
      {content.substitute_page_slug ? (
        <Link
          href={pagePath("substitute", content.substitute_page_slug)}
          className="mt-2 inline-block text-sm font-medium underline hover:text-accent"
        >
          Full substitutes guide →
        </Link>
      ) : null}

      <FaqSection faqs={content.faqs} />

      <RelatedLinks heading="Related recipes" templateType="recipe_or_dish" slugs={content.related_recipe_slugs} />
    </main>
  );
}
