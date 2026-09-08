import type { Metadata } from "next";
import Link from "next/link";
import { searchPages } from "@/lib/api";
import { pagePath } from "@/lib/seo";
import Breadcrumbs from "@/components/Breadcrumbs";
import StockPhotoSlot from "@/components/StockPhotoSlot";

export const metadata: Metadata = {
  title: "Search",
  // Search results are per-query and low-value for organic discovery --
  // the pages they link to are what should get indexed, not this page.
  robots: { index: false, follow: true },
};

const TEMPLATE_LABELS: Record<string, string> = {
  recipe_or_dish: "Recipe",
  ingredient_hub: "Ingredient",
  howto_technique: "How-To",
  definition: "Definition",
  comparison: "Comparison",
  substitute: "Substitute",
  category_roundup: "Collection",
  tool_page: "Tool",
  static_page: "Page",
};

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  const query = q?.trim() ?? "";
  const results = query ? await searchPages(query) : [];

  const breadcrumbItems = [
    { label: "Home", href: "/" },
    { label: "Food", href: "/food" },
    { label: "Search" },
  ];

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <Breadcrumbs items={breadcrumbItems} />
      <h1 className="mt-4 text-2xl font-bold">
        {query ? (
          <>
            Search results for <span className="text-accent">&ldquo;{query}&rdquo;</span>
          </>
        ) : (
          "Search"
        )}
      </h1>

      {!query ? (
        <p className="mt-4 text-ink/60">Enter a search term above to find recipes, ingredients, and guides.</p>
      ) : results.length === 0 ? (
        <p className="mt-4 text-ink/60">
          No results for &ldquo;{query}&rdquo;. Try a different or more general term.
        </p>
      ) : (
        <ul className="mt-6 divide-y divide-ink/10">
          {results.map((page) => (
            <li key={page.slug} className="py-4">
              <Link href={pagePath(page.template_type, page.slug)} className="flex items-center gap-4">
                <div className="h-16 w-16 shrink-0 overflow-hidden rounded-lg">
                  <StockPhotoSlot
                    query={page.hero_image_query ?? page.title}
                    alt={page.image_alt}
                    imageUrl={page.image_url}
                    aspect="thumbnail"
                  />
                </div>
                <span className="min-w-0">
                  <span className="block text-lg font-semibold hover:text-accent">{page.title}</span>
                  <span className="mt-1 block text-xs uppercase tracking-wide text-ink/40">
                    {TEMPLATE_LABELS[page.template_type] ?? page.template_type}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
