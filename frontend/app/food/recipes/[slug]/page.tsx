import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPage } from "@/lib/api";
import type { RecipeContent } from "@/lib/types";
import StockPhotoSlot from "@/components/StockPhotoSlot";
import RecipeIngredientsPanel from "@/components/RecipeIngredientsPanel";
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
      {/* `image` is only included once a real photo exists (see
          backend/app/fetch_stock_images.py) -- Recipe rich-result
          eligibility requires a real, reachable image, so omitting it
          entirely is more correct than pointing at the placeholder. */}
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "Recipe",
          name: page.title,
          description: content.meta_description ?? content.why_it_works,
          image: content.image_url,
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
        <StockPhotoSlot
          query={content.hero_image_query}
          imageUrl={content.image_url}
          attribution={content.image_attribution}
          className="mt-4"
        />

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

        {/* Depth added below the recipe, never between the user and the
            instructions -- see PAGE_TEMPLATES.md's Recipe Page spec. */}
        {content.tips_and_variations && content.tips_and_variations.length > 0 ? (
          <>
            <h2 className="mt-8 text-xl font-bold">Tips &amp; variations</h2>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-ink/80">
              {content.tips_and_variations.map((tip, i) => (
                <li key={i}>{tip}</li>
              ))}
            </ul>
          </>
        ) : null}

        {content.storage_and_reheating ? (
          <>
            <h2 className="mt-8 text-xl font-bold">Storage &amp; reheating</h2>
            <p className="mt-2 text-sm text-ink/80">{content.storage_and_reheating}</p>
          </>
        ) : null}

        {content.nutrition_note ? (
          <>
            <h2 className="mt-8 text-xl font-bold">Nutrition</h2>
            <p className="mt-2 text-sm text-ink/80">{content.nutrition_note}</p>
          </>
        ) : null}

        {content.faqs && content.faqs.length > 0 ? (
          <>
            <JsonLd
              data={{
                "@context": "https://schema.org",
                "@type": "FAQPage",
                mainEntity: content.faqs.map((faq) => ({
                  "@type": "Question",
                  name: faq.question,
                  acceptedAnswer: { "@type": "Answer", text: faq.answer },
                })),
              }}
            />
            <h2 className="mt-8 text-xl font-bold">FAQ</h2>
            <div className="mt-3 space-y-4">
              {content.faqs.map((faq, i) => (
                <div key={i}>
                  <p className="font-semibold">{faq.question}</p>
                  <p className="mt-1 text-sm text-ink/80">{faq.answer}</p>
                </div>
              ))}
            </div>
          </>
        ) : null}
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
