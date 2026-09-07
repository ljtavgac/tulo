import { Fragment } from "react";
import { notFound } from "next/navigation";
import { getPage } from "@/lib/api";
import type { CategoryRoundupContent } from "@/lib/types";
import RecipeCard from "@/components/RecipeCard";
import AdSlot from "@/components/AdSlot";

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

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="text-3xl font-bold">{page.title}</h1>
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
    </main>
  );
}
