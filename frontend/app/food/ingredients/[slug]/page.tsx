import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPage } from "@/lib/api";
import type { IngredientHubContent } from "@/lib/types";
import StockPhotoSlot from "@/components/StockPhotoSlot";
import JsonLd from "@/components/JsonLd";
import Breadcrumbs from "@/components/Breadcrumbs";
import Link from "next/link";
import { buildBreadcrumbList, buildPageMetadata, pagePath } from "@/lib/seo";
import { sectionForTemplate } from "@/lib/taxonomy";

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

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <Breadcrumbs items={breadcrumbItems} />
      <JsonLd data={buildBreadcrumbList(breadcrumbItems)} />
      <h1 className="mt-4 text-3xl font-bold">{page.title}</h1>
      <StockPhotoSlot
        query={content.hero_image_query}
        imageUrl={content.image_url}
        attribution={content.image_attribution}
        className="mt-4"
      />

      <p className="mt-4 text-ink/80">{content.description}</p>

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
      <p className="mt-2 text-ink/80">{content.storage}</p>

      <h2 className="mt-8 text-xl font-bold">How to use</h2>
      <p className="mt-2 text-ink/80">{content.uses}</p>

      <h2 className="mt-8 text-xl font-bold">Nutrition</h2>
      <p className="mt-2 text-ink/80">{content.nutrition_note}</p>

      {content.recipe_slugs.length > 0 ? (
        <>
          <h2 className="mt-8 text-xl font-bold">Recipes using {page.title.toLowerCase()}</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
            {content.recipe_slugs.map((s) => (
              <li key={s}>
                <Link href={pagePath("recipe_or_dish", s)} className="underline hover:text-accent">
                  {s.replace(/-/g, " ")}
                </Link>
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {content.related_ingredient_slugs.length > 0 ? (
        <>
          <h2 className="mt-8 text-xl font-bold">Related ingredients</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
            {content.related_ingredient_slugs.map((s) => (
              <li key={s}>
                <Link href={pagePath("ingredient_hub", s)} className="underline hover:text-accent">
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
