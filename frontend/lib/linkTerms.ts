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

// Definition ("What Is X?") page titles read as full questions, not literal
// terms, so they're excluded from LINKABLE_TEMPLATE_TYPES above -- but the
// bare term they're defining (once the question wrapper is stripped) is
// exactly the kind of short, reused name worth auto-linking, e.g. "fold" or
// "sear" inside a recipe's own instructions. Same derivation the definition
// page itself already uses for its DefinedTerm JSON-LD.
function bareTermFromDefinitionTitle(title: string): string {
  return title.replace(/^What Is /i, "").replace(/\?.*$/, "");
}

// Builds the dictionary of page names inline prose can auto-link to. This
// genuinely needs every page of these template types (unlike RelatedLinks
// or the homepage carousels, it can't safely sample a subset -- an older
// recipe or ingredient dropped from the source list would silently stop
// being auto-linked). `lean: true` is what makes running this on every
// single content page view affordable anyway: it skips image_url/
// image_attribution (never used here) and serves from the backend's
// process-lifetime cache instead of a live, full-table query each time --
// see /pages's `lean` param docs for why that's safe with no staleness
// risk (title/slug/link_terms never change at runtime, unlike photos).
export async function getLinkTerms(excludeSlug?: string): Promise<LinkTerm[]> {
  const [pageLists, definitionPages] = await Promise.all([
    Promise.all(LINKABLE_TEMPLATE_TYPES.map((t) => listPages(t, { lean: true }))),
    listPages("definition", { lean: true }),
  ]);
  const terms = pageLists
    .flat()
    .filter((p) => p.slug !== excludeSlug)
    .map((p) => ({ name: p.title, href: pagePath(p.template_type, p.slug) }));
  const definitionTerms = definitionPages
    .filter((p) => p.slug !== excludeSlug)
    .flatMap((p) => {
      const href = pagePath(p.template_type, p.slug);
      // link_terms (technique pages: "sear", "seared", ...) take priority
      // over the title-derived bare term -- for a technique, the title's
      // gerund form ("Searing") often isn't even one of the literal words
      // worth linking, so this doesn't just supplement it, it replaces it.
      if (p.link_terms && p.link_terms.length > 0) {
        return p.link_terms.map((term) => ({ name: term, href }));
      }
      return [{ name: bareTermFromDefinitionTitle(p.title), href }];
    });
  return [...terms, ...definitionTerms].slice(0, MAX_TERMS);
}
