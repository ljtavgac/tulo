import type { Metadata } from "next";
import Link from "next/link";
import { getPage } from "@/lib/api";
import type { HomepageContent, RecipeContent } from "@/lib/types";
import RecipeCard from "@/components/RecipeCard";
import JsonLd from "@/components/JsonLd";
import { SITE_NAME, SITE_URL, pagePath } from "@/lib/seo";
import { FOOD_INDEX_SECTIONS } from "@/lib/taxonomy";

export async function generateMetadata(): Promise<Metadata> {
  const page = await getPage<HomepageContent>("homepage");
  const description = page?.content.meta_description;

  return {
    title: { absolute: SITE_NAME },
    description,
    alternates: { canonical: "/food" },
    openGraph: { title: SITE_NAME, description, url: "/food" },
  };
}

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
  const recipesSection = FOOD_INDEX_SECTIONS.find((s) => s.key === "recipes")!;
  const collectionsSection = FOOD_INDEX_SECTIONS.find((s) => s.key === "collections")!;

  // featured_recipe_slugs is a bare list of slugs, not full page data, so
  // each one needs its own fetch to get a real title/image instead of
  // guessing a title from the slug text and showing a placeholder image.
  const featuredRecipes = await Promise.all(
    content.featured_recipe_slugs.map((slug) => getPage<RecipeContent>(slug))
  );

  return (
    <main>
      {/* No SearchAction here -- the header's search bar isn't wired to a
          working /search route yet, and structured data should only claim
          capabilities the page actually has. Add SearchAction once search
          is real. */}
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "WebSite",
          name: SITE_NAME,
          url: SITE_URL,
        }}
      />
      <section className="mx-auto max-w-3xl px-4 py-20 text-center">
        <h1 className="text-3xl font-bold leading-snug md:text-4xl">{content.positioning_statement}</h1>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link
            href={recipesSection.path}
            className="rounded-full bg-accent px-6 py-2.5 text-sm font-semibold text-cream hover:bg-accent/90"
          >
            Browse Recipes
          </Link>
          <Link
            href={collectionsSection.path}
            className="rounded-full border border-ink/20 px-6 py-2.5 text-sm font-semibold hover:border-accent hover:text-accent"
          >
            See Collections
          </Link>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-10">
        <h2 className="text-xl font-bold">Featured recipes</h2>
        <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
          {content.featured_recipe_slugs.map((slug, i) => {
            const recipe = featuredRecipes[i];
            return (
              <RecipeCard
                key={slug}
                title={recipe?.title ?? slug.replace(/-/g, " ")}
                imageQuery={recipe?.content.hero_image_query ?? slug.replace(/-/g, " ")}
                imageUrl={recipe?.content.image_url}
                imageAttribution={recipe?.content.image_attribution}
                slug={recipe ? slug : null}
              />
            );
          })}
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-10">
        <h2 className="text-xl font-bold">Browse by category</h2>
        <div className="mt-4 flex flex-wrap gap-3">
          {content.category_links.map((link) => (
            <Link
              key={link.slug}
              href={pagePath("category_roundup", link.slug)}
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
              href={pagePath("tool_page", tool.slug)}
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
