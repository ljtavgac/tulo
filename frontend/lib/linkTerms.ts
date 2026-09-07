import { listPages } from "./api";
import { pagePath } from "./seo";

export interface LinkTerm {
  name: string;
  href: string;
}

// Ingredients, recipes, and techniques all have short, literal, commonly
// reused names (unlike Comparisons/Substitutes/Collections, whose titles
// read as full sentences and are unlikely to appear verbatim inside
// someone else's prose) -- these are the page types worth auto-linking
// from body text elsewhere on the site.
const LINKABLE_TEMPLATE_TYPES = ["ingredient_hub", "recipe_or_dish", "howto_technique"];

// At today's content scale (dozens of pages) scanning every linkable title
// against every prose block is cheap. At the thousands-of-articles scale
// launch_plan.md describes, matching against every single title stops
// being the right approach -- that's the point to move to a precomputed
// index (built at content-generation time) or a real search-backed
// lookup instead of a client-side regex scan. Capping the term count here
// keeps today's implementation simple without pretending it's the design
// that scales to that batch size.
const MAX_TERMS = 300;

// Builds the dictionary of page names inline prose can auto-link to.
// listPages() is cached for an hour (see lib/api.ts), so this is a
// handful of cached fetches, not a per-render cost.
export async function getLinkTerms(excludeSlug?: string): Promise<LinkTerm[]> {
  const pageLists = await Promise.all(LINKABLE_TEMPLATE_TYPES.map((t) => listPages(t)));
  return pageLists
    .flat()
    .filter((p) => p.slug !== excludeSlug)
    .map((p) => ({ name: p.title, href: pagePath(p.template_type, p.slug) }))
    .slice(0, MAX_TERMS);
}
