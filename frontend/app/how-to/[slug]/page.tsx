import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPage } from "@/lib/api";
import type { HowToContent } from "@/lib/types";
import StockPhotoSlot from "@/components/StockPhotoSlot";
import JsonLd from "@/components/JsonLd";
import Link from "next/link";
import { buildPageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const page = await getPage<HowToContent>(slug);
  if (!page || page.template_type !== "howto_technique") return {};
  return buildPageMetadata(page);
}

export default async function HowToPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const page = await getPage<HowToContent>(slug);
  if (!page || page.template_type !== "howto_technique") notFound();

  const { content } = page;

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "HowTo",
          name: page.title,
          description: content.meta_description,
          image: content.image_url,
          step: content.steps.map((step) => ({
            "@type": "HowToStep",
            text: step,
          })),
        }}
      />
      <h1 className="text-3xl font-bold">{page.title}</h1>
      <StockPhotoSlot
        query={content.hero_image_query}
        imageUrl={content.image_url}
        attribution={content.image_attribution}
        className="mt-4"
      />

      <h2 className="mt-8 text-xl font-bold">Steps</h2>
      <ol className="mt-3 space-y-3">
        {content.steps.map((step, i) => (
          <li key={i} className="flex gap-3 text-sm">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ink text-xs font-semibold text-cream">
              {i + 1}
            </span>
            <span className="pt-0.5">{step}</span>
          </li>
        ))}
      </ol>

      <h2 className="mt-8 text-xl font-bold">Common mistakes</h2>
      <ul className="mt-3 space-y-2">
        {content.common_mistakes.map((mistake, i) => (
          <li key={i} className="rounded-lg border border-ink/10 p-3 text-sm text-ink/80">
            {mistake}
          </li>
        ))}
      </ul>

      <h2 className="mt-8 text-xl font-bold">Equipment</h2>
      <ul className="mt-3 flex flex-wrap gap-2">
        {content.equipment.map((item) => (
          <li key={item} className="rounded-full border border-ink/20 px-3 py-1 text-xs">
            {item}
          </li>
        ))}
      </ul>

      {content.recipe_slugs.length > 0 ? (
        <>
          <h2 className="mt-8 text-xl font-bold">Recipes using this technique</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
            {content.recipe_slugs.map((s) => (
              <li key={s}>
                <Link href={`/recipes/${s}`} className="underline hover:text-accent">
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
