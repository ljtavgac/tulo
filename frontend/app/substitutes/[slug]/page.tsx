import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPage } from "@/lib/api";
import type { SubstituteContent } from "@/lib/types";
import Link from "next/link";
import { buildPageMetadata } from "@/lib/seo";

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

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-3xl font-bold">{page.title}</h1>
      {content.hub_page_slug ? (
        <Link
          href={`/ingredients/${content.hub_page_slug}`}
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

      {content.recipe_slugs.length > 0 ? (
        <>
          <h2 className="mt-8 text-xl font-bold">Recipes that work well with these substitutes</h2>
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
