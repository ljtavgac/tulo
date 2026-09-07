import Link from "next/link";
import { listPages } from "@/lib/api";
import { pagePath } from "@/lib/seo";

// Every content template links out to related slugs (recipe_slugs,
// related_ingredient_slugs, etc.), but those are bare slug arrays, not
// {title, slug} pairs -- rendering them used to guess a title by turning
// hyphens into spaces ("banana-nut-bread" -> "banana nut bread"), which
// doesn't match the page's real title or capitalization. listPages() is
// cached for an hour (see lib/api.ts), so filtering it down to the
// requested slugs here is one cached fetch instead of one round trip per
// link, and it gives the real title.
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
      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
        {matched.map((p) => (
          <li key={p.slug}>
            <Link href={pagePath(p.template_type, p.slug)} className="underline hover:text-accent">
              {p.title}
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
