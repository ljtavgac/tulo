export interface PageSummary {
  slug: string;
  template_type: string;
  title: string;
  image_url?: string;
  image_attribution?: ImageAttribution;
  hero_image_query?: string;
}

export interface PageRecord<T = Record<string, unknown>> {
  slug: string;
  template_type: string;
  title: string;
  status: string;
  batch_number: number | null;
  content: T;
  created_at: string;
}

export interface RecipeIngredient {
  name: string;
  base_qty: number;
  unit_us: string;
  base_qty_metric: number;
  unit_metric: string;
  hub_slug: string | null;
  // Populated server-side (not stored in the recipe's own content) from
  // hub_slug's ingredient hub page, for ingredients that have one --
  // backs the "I don't have this" swap tool. Only substitutes with a
  // ratio_multiplier are swappable by pure math; others aren't included.
  available_substitutes?: IngredientSubstitute[];
}

// For a discrete count of items (eggs, bananas, cloves of garlic) rather
// than a real measurement, set unit_metric equal to unit_us (and
// base_qty_metric equal to base_qty) instead of converting to a weight --
// "1 banana" doesn't have a meaningful, universally-agreed gram equivalent
// the way "1 cup" does. RecipeIngredientsPanel checks for this equality to
// decide whether to treat an ingredient as a real US/metric conversion.

export interface LinkRef {
  title: string;
  slug: string;
}

// Present once backend/app/fetch_stock_images.py has found a real photo
// for a page's image query; absent (undefined) means keep showing the
// placeholder. Attribution is required by Unsplash's API terms and good
// practice for Pexels.
export interface ImageAttribution {
  photographer: string;
  photographer_url: string;
  source: "unsplash" | "pexels";
}

export interface Faq {
  question: string;
  answer: string;
}

export interface RecipeContent {
  meta_description?: string;
  hero_image_query: string;
  image_url?: string;
  image_attribution?: ImageAttribution;
  why_it_works: string;
  prep_time_minutes: number;
  cook_time_minutes: number;
  total_time_minutes: number;
  servings: number;
  ingredients: RecipeIngredient[];
  instructions: string[];
  // Depth added for SEO without violating the "no life story" positioning
  // (see PAGE_TEMPLATES.md): structured reference content, not narrative --
  // FAQs, tips, storage, and nutrition are all common real search intents
  // ("can I freeze X", "why is my X dense") that a short story wouldn't
  // answer anyway. All optional since older/batch content may predate them.
  tips_and_variations?: string[];
  storage_and_reheating?: string;
  nutrition_note?: string;
  faqs?: Faq[];
  technique_link: LinkRef | null;
  related_recipe_slugs: string[];
  category_link: LinkRef | null;
}

export interface IngredientSubstitute {
  name: string;
  ratio: string;
  note: string;
  // A precise "amount of substitute per 1 unit of the original" multiplier,
  // for substitutes that actually reduce to one (most are 1, e.g.
  // cornstarch -> flour is 2). null for substitutes that don't -- an
  // additive combo (flour + a second ingredient) or a deliberately vague
  // ratio ("slightly more") can't be swapped in by pure math, so the
  // ingredient swap tool only offers substitutes where this is set.
  ratio_multiplier?: number | null;
}

export interface IngredientHubContent {
  meta_description?: string;
  hero_image_query: string;
  image_url?: string;
  image_attribution?: ImageAttribution;
  description: string;
  substitutes: IngredientSubstitute[];
  substitute_page_slug: string | null;
  storage: string;
  uses: string;
  nutrition_note: string;
  buying_tips?: string;
  pairing_suggestions?: string;
  variety_notes?: string;
  faqs?: Faq[];
  recipe_slugs: string[];
  related_ingredient_slugs: string[];
}

export interface HowToContent {
  meta_description?: string;
  hero_image_query: string;
  image_url?: string;
  image_attribution?: ImageAttribution;
  intro: string;
  steps: string[];
  common_mistakes: string[];
  equipment: string[];
  faqs?: Faq[];
  recipe_slugs: string[];
  related_technique_slugs: string[];
}

export interface DefinitionContent {
  meta_description?: string;
  hero_image_query: string;
  image_url?: string;
  image_attribution?: ImageAttribution;
  direct_answer: string;
  expanded_explanation: string;
  usage_origin: string;
  substitute_note: string;
  substitute_page_slug: string | null;
  faqs?: Faq[];
  related_recipe_slugs: string[];
}

export interface ComparisonRow {
  attribute: string;
  item_a: string;
  item_b: string;
}

export interface ComparisonSection {
  heading: string;
  body: string;
}

export interface ComparisonContent {
  meta_description?: string;
  hero_image_query?: string;
  image_url?: string;
  image_attribution?: ImageAttribution;
  item_a_name: string;
  item_b_name: string;
  comparison_table: ComparisonRow[];
  verdict: string;
  sections: ComparisonSection[];
  faqs?: Faq[];
  item_a_link: LinkRef | null;
  item_b_link: LinkRef | null;
}

export interface RankedSubstitute {
  name: string;
  ratio: string;
  best_for: string;
  note: string;
  ratio_multiplier?: number | null;
}

export interface SubstituteContent {
  meta_description?: string;
  hero_image_query?: string;
  image_url?: string;
  image_attribution?: ImageAttribution;
  ranked_substitutes: RankedSubstitute[];
  baking_vs_cooking_note: string;
  faqs?: Faq[];
  hub_page_slug: string | null;
  recipe_slugs: string[];
}

export interface RecipeCardData {
  title: string;
  slug: string | null;
  description: string;
  image_query: string;
  image_url?: string;
  image_attribution?: ImageAttribution;
}

export interface SubCategory {
  label: string;
  items: string[];
}

export interface CategoryRoundupContent {
  meta_description?: string;
  intro: string;
  recipe_cards: RecipeCardData[];
  sub_categories: SubCategory[];
  faqs?: Faq[];
  related_collection_slugs: string[];
}

export interface HomepageContent {
  meta_description?: string;
  featured_recipe_slugs: string[];
  category_links: LinkRef[];
  tool_links: LinkRef[];
  positioning_statement: string;
}
