import { listPages } from "@/lib/api";
import { pagePath } from "@/lib/seo";
import PageTile from "./PageTile";

// Every content template links out to related slugs (recipe_slugs,
// related_ingredient_slugs, etc.), but those are bare slug arrays, not
// {title, slug, image} data -- rendering them used to guess a title by
// turning hyphens into spaces ("banana-nut-bread" -> "banana nut bread"),
// which doesn't match the page's real title or capitalization, and gave no
// visual sense of what the linked page actually is. listPages() is cached
// for an hour (see lib/api.ts) and already returns each page's real title
// and image data, so filtering it down to the requested slugs here is one
// cached fetch instead of one round trip per link, and it's enough to
// render real photo tiles instead of a flat bulleted text list.
export default async function RelatedLinks({
  heading,
  templateType,
  slugs,
}: {
  heading: string;
  templateType: string;
  slugs: string[];
}) {
  if (slugs.length === 0) return null;

  const pages = await listPages(templateType);
  const bySlug = new Map(pages.map((p) => [p.slug, p]));
  const matched = slugs.map((s) => bySlug.get(s)).filter((p): p is NonNullable<typeof p> => Boolean(p));

  if (matched.length === 0) return null;

  return (
    <>
      <h2 className="mt-8 text-xl font-bold">{heading}</h2>
      <ul className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-3">
        {matched.map((p) => (
          <li key={p.slug}>
            <PageTile
              href={pagePath(p.template_type, p.slug)}
              title={p.title}
              imageQuery={p.hero_image_query ?? p.title}
              imageUrl={p.image_url}
              imageAttribution={p.image_attribution}
            />
          </li>
        ))}
      </ul>
    </>
  );
}
