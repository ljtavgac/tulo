// Small helpers for the Recipe page's JSON-LD (frontend/app/food/recipes/
// [slug]/page.tsx) -- both address specific, non-critical suggestions
// Google Search Console flagged on the live site (2026-09-18): a missing
// recipeCuisine field, and a missing "name" on each recipeInstructions
// step.

// Maps a category_roundup collection slug to its schema.org recipeCuisine
// value, for collections that are genuinely a cuisine/region (not an
// ingredient- or dish-type collection like "taco-recipes" or
// "pie-recipes"). Deliberately a small, explicit, hand-maintained list --
// recipeCuisine should never be guessed from a slug/title pattern, only
// asserted for a collection that unambiguously names a cuisine. A recipe
// whose category_link points anywhere else (or is null) gets no
// recipeCuisine at all, which is correct: omitting the field is a
// non-critical suggestion, guessing wrong is a real accuracy problem.
// Extend this list by hand if a new cuisine collection is added later --
// it won't pick one up automatically.
const CUISINE_COLLECTIONS: Record<string, string> = {
  "italian-recipes": "Italian",
  "mexican-recipes": "Mexican",
  "polish-recipes": "Polish",
  "indian-recipes": "Indian",
  "chinese-recipes": "Chinese",
  "japanese-recipes": "Japanese",
  "french-recipes": "French",
  "thai-recipes": "Thai",
  "cajun-recipes": "Cajun",
};

export function cuisineForCategorySlug(slug: string | undefined | null): string | undefined {
  if (!slug) return undefined;
  return CUISINE_COLLECTIONS[slug];
}

// Derives a short HowToStep "name" from a step's full instruction text --
// mechanical, not a content-review pass (1000+ recipes make a hand-written
// name per step impractical, and Google lists this as a non-critical
// suggestion, not a requirement). Prefers the first full sentence; when
// that's still too long, backs off to a comma break if one exists past a
// reasonable minimum length, otherwise truncates at the last word boundary
// under maxLength. Spot-checked against real steps (banana-nut-bread,
// chicken-broccoli-rice-casserole) before rollout -- reads as a reasonable
// short label in every case checked, not perfect prose but accurate.
export function deriveStepName(stepText: string, maxLength = 60): string {
  const sentenceMatch = stepText.match(/^.*?[.!?]/);
  let candidate = (sentenceMatch ? sentenceMatch[0] : stepText).replace(/[.!?]+$/, "").trim();

  if (candidate.length > maxLength) {
    const commaIdx = candidate.lastIndexOf(",", maxLength);
    if (commaIdx > 20) {
      candidate = candidate.slice(0, commaIdx).trim();
    } else {
      const truncated = candidate.slice(0, maxLength);
      const lastSpace = truncated.lastIndexOf(" ");
      candidate = (lastSpace > 20 ? truncated.slice(0, lastSpace) : truncated).trim();
    }
  }

  return candidate;
}
