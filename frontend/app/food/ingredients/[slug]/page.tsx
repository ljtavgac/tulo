import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPage } from "@/lib/api";
import type { IngredientHubContent } from "@/lib/types";
import StockPhotoSlot from "@/components/StockPhotoSlot";
import JsonLd from "@/components/JsonLd";
import Breadcrumbs from "@/components/Breadcrumbs";
import FaqSection from "@/components/FaqSection";
import RelatedLinks from "@/components/RelatedLinks";
import ToolCallout from "@/components/ToolCallout";
import AdSlot from "@/components/AdSlot";
import LinkifiedText from "@/components/LinkifiedText";
import InSeasonBadge from "@/components/InSeasonBadge";
import Link from "next/link";
import { buildBreadcrumbList, buildPageMetadata, pagePath } from "@/lib/seo";
import { sectionForTemplate } from "@/lib/taxonomy";
import { getLinkTerms } from "@/lib/linkTerms";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const page = await getPage<IngredientHubContent>(slug);
  if (!page || page.template_type !== "ingredient_hub") return {};
  return buildPageMetadata(page);
}

export default async function IngredientHubPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const page = await getPage<IngredientHubContent>(slug);
  if (!page || page.template_type !== "ingredient_hub") notFound();

  const { content } = page;

  const section = sectionForTemplate(page.template_type)!;
  const breadcrumbItems = [
    { label: "Home", href: "/" },
    { label: "Food", href: "/food" },
    { label: section.label, href: section.path },
    { label: page.title },
  ];
  const linkTerms = await getLinkTerms(slug);

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <Breadcrumbs items={breadcrumbItems} />
      <JsonLd data={buildBreadcrumbList(breadcrumbItems)} />
      <h1 className="mt-4 text-3xl font-bold">{page.title}</h1>
      <InSeasonBadge slug={slug} />
      <StockPhotoSlot
        query={content.hero_image_query}
        imageUrl={content.image_url}
        attribution={content.image_attribution}
        className="mt-4"
      />

      <p className="mt-4 text-ink/80">
        <LinkifiedText text={content.description} terms={linkTerms} />
      </p>

      {content.variety_notes ? (
        <>
          <h2 className="mt-8 text-xl font-bold">Varieties</h2>
          <p className="mt-2 text-ink/80">
            <LinkifiedText text={content.variety_notes} terms={linkTerms} />
          </p>
        </>
      ) : null}

      {content.buying_tips ? (
        <>
          <h2 className="mt-8 text-xl font-bold">Buying tips</h2>
          <p className="mt-2 text-ink/80">
            <LinkifiedText text={content.buying_tips} terms={linkTerms} />
          </p>
        </>
      ) : null}

      <h2 className="mt-8 text-xl font-bold">Substitutes</h2>
      <ul className="mt-3 space-y-3">
        {content.substitutes.map((sub) => (
          <li key={sub.name} className="rounded-lg border border-ink/10 p-3 text-sm">
            <p className="font-semibold">
              {sub.name} <span className="font-normal text-ink/50">— {sub.ratio}</span>
            </p>
            <p className="mt-1 text-ink/70">{sub.note}</p>
          </li>
        ))}
      </ul>
      {content.substitute_page_slug ? (
        <Link
          href={pagePath("substitute", content.substitute_page_slug)}
          className="mt-3 inline-block text-sm font-medium underline hover:text-accent"
        >
          See the full substitutes guide →
        </Link>
      ) : null}

      <h2 className="mt-8 text-xl font-bold">Storage</h2>
      <p className="mt-2 text-ink/80">
        <LinkifiedText text={content.storage} terms={linkTerms} />
      </p>

      <h2 className="mt-8 text-xl font-bold">How to use</h2>
      <p className="mt-2 text-ink/80">
        <LinkifiedText text={content.uses} terms={linkTerms} />
      </p>

      {content.pairing_suggestions ? (
        <>
          <h2 className="mt-8 text-xl font-bold">What it pairs with</h2>
          <p className="mt-2 text-ink/80">
            <LinkifiedText text={content.pairing_suggestions} terms={linkTerms} />
          </p>
        </>
      ) : null}

      <div className="my-8">
        <AdSlot variant="in-content" />
      </div>

      <h2 className="mt-8 text-xl font-bold">Nutrition</h2>
      <p className="mt-2 text-ink/80">{content.nutrition_note}</p>

      <FaqSection faqs={content.faqs} />

      <ToolCallout
        slug="recipe-generator"
        label={`Have ${page.title.toLowerCase()} on hand? Find recipes with our Recipe Generator`}
        queryParams={{ ingredients: page.title.toLowerCase() }}
      />

      <RelatedLinks
        heading={`Recipes using ${page.title.toLowerCase()}`}
        templateType="recipe_or_dish"
        slugs={content.recipe_slugs}
      />

      <RelatedLinks
        heading="Related ingredients"
        templateType="ingredient_hub"
        slugs={content.related_ingredient_slugs}
      />
    </main>
  );
}
