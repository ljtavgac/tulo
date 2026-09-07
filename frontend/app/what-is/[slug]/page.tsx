import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPage } from "@/lib/api";
import type { DefinitionContent } from "@/lib/types";
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

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "DefinedTerm",
          name: page.title.replace(/^What Is /i, "").replace(/\?.*$/, ""),
          description: content.direct_answer,
        }}
      />
      <h1 className="text-3xl font-bold">{page.title}</h1>

      {/* Direct answer up top, ahead of the hero image -- featured-snippet
          optimized, per the Definition template spec. */}
      <p className="mt-4 rounded-lg bg-ink/5 p-4 text-lg font-medium">{content.direct_answer}</p>

      <StockPhotoSlot query={content.hero_image_query} className="mt-4" />

      <h2 className="mt-8 text-xl font-bold">More detail</h2>
      <p className="mt-2 text-ink/80">{content.expanded_explanation}</p>

      <h2 className="mt-8 text-xl font-bold">Where it's used</h2>
      <p className="mt-2 text-ink/80">{content.usage_origin}</p>

      <h2 className="mt-8 text-xl font-bold">Substitutes</h2>
      <p className="mt-2 text-ink/80">{content.substitute_note}</p>
      {content.substitute_page_slug ? (
        <Link
          href={`/substitutes/${content.substitute_page_slug}`}
          className="mt-2 inline-block text-sm font-medium underline hover:text-accent"
        >
          Full substitutes guide →
        </Link>
      ) : null}

      {content.related_recipe_slugs.length > 0 ? (
        <>
          <h2 className="mt-8 text-xl font-bold">Related recipes</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
            {content.related_recipe_slugs.map((s) => (
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
