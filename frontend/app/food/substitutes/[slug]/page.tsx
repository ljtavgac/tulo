import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPage } from "@/lib/api";
import type { SubstituteContent } from "@/lib/types";
import Link from "next/link";
import JsonLd from "@/components/JsonLd";
import Breadcrumbs from "@/components/Breadcrumbs";
import FaqSection from "@/components/FaqSection";
import RelatedLinks from "@/components/RelatedLinks";
import StockPhotoSlot from "@/components/StockPhotoSlot";
import AdSlot from "@/components/AdSlot";
import { buildBreadcrumbList, buildPageMetadata, pagePath } from "@/lib/seo";
import { sectionForTemplate } from "@/lib/taxonomy";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const page = await getPage<SubstituteContent>(slug);
  if (!page || page.template_type !== "substitute") return {};
  return buildPageMetadata(page);
}

export default async function SubstitutePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const page = await getPage<SubstituteContent>(slug);
  if (!page || page.template_type !== "substitute") notFound();

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
      <h1 className="mt-4 text-3xl font-bold">{page.title}</h1>
      <StockPhotoSlot
        query={content.hero_image_query ?? page.title}
        imageUrl={content.image_url}
        attribution={content.image_attribution}
        className="mt-4"
      />
      {content.hub_page_slug ? (
        <Link
          href={pagePath("ingredient_hub", content.hub_page_slug)}
          className="mt-2 inline-block text-sm font-medium underline hover:text-accent"
        >
          ← Back to the main ingredient page
        </Link>
      ) : null}

      <ol className="mt-6 space-y-4">
        {content.ranked_substitutes.map((sub, i) => (
          <li key={sub.name} className="rounded-lg border border-ink/10 p-4">
            <p className="text-sm font-semibold text-accent">#{i + 1}</p>
            <p className="mt-1 font-semibold">
              {sub.name} <span className="font-normal text-ink/50">— {sub.ratio}</span>
            </p>
            <p className="mt-1 text-xs uppercase tracking-wide text-ink/40">
              Best for: {sub.best_for}
            </p>
            <p className="mt-2 text-sm text-ink/80">{sub.note}</p>
          </li>
        ))}
      </ol>

      <div className="mt-8 rounded-lg bg-ink/5 p-4 text-sm text-ink/80">{content.baking_vs_cooking_note}</div>

      <div className="my-8">
        <AdSlot variant="in-content" />
      </div>

      <FaqSection faqs={content.faqs} />

      <RelatedLinks
        heading="Recipes that work well with these substitutes"
        templateType="recipe_or_dish"
        slugs={content.recipe_slugs}
      />
    </main>
  );
}
