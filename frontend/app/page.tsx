import Link from "next/link";
import { getPage } from "@/lib/api";
import type { HomepageContent } from "@/lib/types";
import RecipeCard from "@/components/RecipeCard";

export default async function HomePage() {
  const page = await getPage<HomepageContent>("homepage");

  if (!page) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-16 text-center">
        <p>Could not load homepage content from the backend.</p>
      </main>
    );
  }

  const { content } = page;

  return (
    <main>
      <section className="mx-auto max-w-3xl px-4 py-16 text-center">
        <h1 className="text-4xl font-bold">Tulo</h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-ink/70">{content.positioning_statement}</p>
        <form className="mx-auto mt-8 flex max-w-md gap-2" role="search">
          <input
            type="search"
            placeholder="Search recipes, ingredients, techniques…"
            className="flex-1 rounded-full border border-ink/20 px-4 py-2 text-sm focus:border-accent focus:outline-none"
          />
          <button
            type="submit"
            className="rounded-full bg-accent px-5 py-2 text-sm font-semibold text-cream"
          >
            Search
          </button>
        </form>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-10">
        <h2 className="text-xl font-bold">Featured recipes</h2>
        <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
          {content.featured_recipe_slugs.map((slug) => (
            <RecipeCard
              key={slug}
              title={slug.replace(/-/g, " ")}
              imageQuery={slug.replace(/-/g, " ")}
              slug={slug}
            />
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-10">
        <h2 className="text-xl font-bold">Browse by category</h2>
        <div className="mt-4 flex flex-wrap gap-3">
          {content.category_links.map((link) => (
            <Link
              key={link.slug}
              href={`/collections/${link.slug}`}
              className="rounded-full border border-ink/20 px-4 py-2 text-sm font-medium hover:border-accent hover:text-accent"
            >
              {link.title}
            </Link>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-10">
        <h2 className="text-xl font-bold">Kitchen tools</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          {content.tool_links.map((tool) => (
            <Link
              key={tool.slug}
              href={`/tools/${tool.slug}`}
              className="rounded-lg border border-ink/10 p-4 text-sm font-semibold hover:border-accent"
            >
              {tool.title}
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
