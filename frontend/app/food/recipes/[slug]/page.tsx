import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPage } from "@/lib/api";
import type { RecipeContent } from "@/lib/types";
import StockPhotoSlot from "@/components/StockPhotoSlot";
import RecipeIngredientsPanel from "@/components/RecipeIngredientsPanel";
import ShopIngredientsButton from "@/components/ShopIngredientsButton";
import AdSlot from "@/components/AdSlot";
import JsonLd from "@/components/JsonLd";
import Breadcrumbs from "@/components/Breadcrumbs";
import Link from "next/link";
import { buildBreadcrumbList, buildPageMetadata, minutesToIso8601, pagePath } from "@/lib/seo";
import { sectionForTemplate } from "@/lib/taxonomy";
import { formatUsQuantity } from "@/lib/format";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const page = await getPage<RecipeContent>(slug);
  if (!page || page.template_type !== "recipe_or_dish") return {};
  return buildPageMetadata(page);
}

export default async function RecipePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const page = await getPage<RecipeContent>(slug);
  if (!page || page.template_type !== "recipe_or_dish") notFound();

  const { content } = page;

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
      <div className="mt-4 grid gap-8 lg:grid-cols-[1fr_260px]">
      {/* No `image` field yet -- StockPhotoSlot is a placeholder, not a
          real photo URL, and Recipe rich-result eligibility requires a
          real, reachable image. Add it once stock photos are wired up. */}
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "Recipe",
          name: page.title,
          description: content.meta_description ?? content.why_it_works,
          prepTime: minutesToIso8601(content.prep_time_minutes),
          cookTime: minutesToIso8601(content.cook_time_minutes),
          totalTime: minutesToIso8601(content.total_time_minutes),
          recipeYield: `${content.servings} servings`,
          recipeIngredient: content.ingredients.map(
            (ing) => `${formatUsQuantity(ing.base_qty)} ${ing.unit_us} ${ing.name}`
          ),
          recipeInstructions: content.instructions.map((step) => ({
            "@type": "HowToStep",
            text: step,
          })),
        }}
      />
      <article>
        <h1 className="text-3xl font-bold">{page.title}</h1>
        <StockPhotoSlot query={content.hero_image_query} className="mt-4" />

        <p className="mt-4 text-ink/80">{content.why_it_works}</p>

        <dl className="mt-4 grid grid-cols-2 gap-3 rounded-lg border border-ink/10 p-4 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-ink/50">Prep</dt>
            <dd className="font-semibold">{content.prep_time_minutes} min</dd>
          </div>
          <div>
            <dt className="text-ink/50">Cook</dt>
            <dd className="font-semibold">{content.cook_time_minutes} min</dd>
          </div>
          <div>
            <dt className="text-ink/50">Total</dt>
            <dd className="font-semibold">{content.total_time_minutes} min</dd>
          </div>
          <div>
            <dt className="text-ink/50">Servings</dt>
            <dd className="font-semibold">{content.servings}</dd>
          </div>
        </dl>

        <div className="mt-6">
          <ShopIngredientsButton />
        </div>

        <h2 className="mt-6 text-xl font-bold">Ingredients</h2>
        <div className="mt-3">
          <RecipeIngredientsPanel ingredients={content.ingredients} baseServings={content.servings} />
        </div>

        <div className="my-6">
          <AdSlot variant="in-content" />
        </div>

        <h2 className="text-xl font-bold">Instructions</h2>
        <ol className="mt-3 space-y-3">
          {content.instructions.map((step, i) => (
            <li key={i} className="flex gap-3 text-sm">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ink text-xs font-semibold text-cream">
                {i + 1}
              </span>
              <span className="pt-0.5">{step}</span>
            </li>
          ))}
        </ol>

        <div className="my-6">
          <AdSlot variant="in-content" />
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            className="rounded-full border border-ink/20 px-4 py-2 text-sm font-medium hover:border-accent hover:text-accent"
          >
            🖨️ Print / PDF
          </button>
          {content.category_link ? (
            <Link
              href={pagePath("category_roundup", content.category_link.slug)}
              className="rounded-full border border-ink/20 px-4 py-2 text-sm font-medium hover:border-accent hover:text-accent"
            >
              More {content.category_link.title}
            </Link>
          ) : null}
          {content.technique_link ? (
            <Link
              href={pagePath("howto_technique", content.technique_link.slug)}
              className="rounded-full border border-ink/20 px-4 py-2 text-sm font-medium hover:border-accent hover:text-accent"
            >
              {content.technique_link.title}
            </Link>
          ) : null}
        </div>
      </article>

      <aside>
        <div className="sticky top-4">
          <AdSlot variant="sidebar" />
        </div>
      </aside>
      </div>
    </main>
  );
}
