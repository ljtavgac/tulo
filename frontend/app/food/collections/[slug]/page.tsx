import type { Metadata } from "next";
import { Fragment } from "react";
import { notFound } from "next/navigation";
import { getPage } from "@/lib/api";
import type { CategoryRoundupContent } from "@/lib/types";
import RecipeCard from "@/components/RecipeCard";
import AdSlot from "@/components/AdSlot";
import JsonLd from "@/components/JsonLd";
import Breadcrumbs from "@/components/Breadcrumbs";
import FaqSection from "@/components/FaqSection";
import { absoluteUrl, buildBreadcrumbList, buildPageMetadata, pagePath } from "@/lib/seo";
import { sectionForTemplate } from "@/lib/taxonomy";
import Link from "next/link";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const page = await getPage<CategoryRoundupContent>(slug);
  if (!page || page.template_type !== "category_roundup") return {};
  return buildPageMetadata(page);
}

export default async function CategoryRoundupPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const page = await getPage<CategoryRoundupContent>(slug);
  if (!page || page.template_type !== "category_roundup") notFound();

  const { content } = page;

  // In-feed ad, blended into the grid every 4 cards, per the roundup
  // placement spec.
  const IN_FEED_INTERVAL = 4;

  const section = sectionForTemplate(page.template_type)!;
  const breadcrumbItems = [
    { label: "Home", href: "/" },
    { label: "Food", href: "/food" },
    { label: section.label, href: section.path },
    { label: page.title },
  ];

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <Breadcrumbs items={breadcrumbItems} />
      <JsonLd data={buildBreadcrumbList(breadcrumbItems)} />
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "ItemList",
          name: page.title,
          itemListElement: content.recipe_cards.map((card, i) => ({
            "@type": "ListItem",
            position: i + 1,
            name: card.title,
            url: card.slug ? absoluteUrl(pagePath("recipe_or_dish", card.slug)) : undefined,
          })),
        }}
      />
      <h1 className="mt-4 text-3xl font-bold">{page.title}</h1>
      <p className="mt-4 max-w-2xl text-ink/80">{content.intro}</p>

      {content.sub_categories.length > 0 ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {content.sub_categories.map((sub) => (
            <span key={sub.label} className="rounded-full border border-ink/20 px-3 py-1 text-xs font-medium">
              {sub.label}
            </span>
          ))}
        </div>
      ) : null}

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
        {content.recipe_cards.map((card, i) => (
          <Fragment key={card.title}>
            <RecipeCard
              title={card.title}
              description={card.description}
              imageQuery={card.image_query}
              imageUrl={card.image_url}
              imageAttribution={card.image_attribution}
              slug={card.slug}
            />
            {(i + 1) % IN_FEED_INTERVAL === 0 && i !== content.recipe_cards.length - 1 ? (
              <div className="col-span-2 sm:col-span-3">
                <AdSlot variant="in-feed" />
              </div>
            ) : null}
          </Fragment>
        ))}
      </div>

      <FaqSection faqs={content.faqs} />

      {content.related_collection_slugs.length > 0 ? (
        <>
          <h2 className="mt-8 text-xl font-bold">Related collections</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
            {content.related_collection_slugs.map((s) => (
              <li key={s}>
                <Link href={pagePath("category_roundup", s)} className="underline hover:text-accent">
                  {s.replace(/-/g, " ")}
                </Link>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </main>
  );
}
