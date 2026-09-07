export interface PageSummary {
  slug: string;
  template_type: string;
  title: string;
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
}

export interface LinkRef {
  title: string;
  slug: string;
}

export interface RecipeContent {
  hero_image_query: string;
  why_it_works: string;
  prep_time_minutes: number;
  cook_time_minutes: number;
  total_time_minutes: number;
  servings: number;
  ingredients: RecipeIngredient[];
  instructions: string[];
  technique_link: LinkRef | null;
  related_recipe_slugs: string[];
  category_link: LinkRef | null;
}

export interface IngredientSubstitute {
  name: string;
  ratio: string;
  note: string;
}

export interface IngredientHubContent {
  hero_image_query: string;
  description: string;
  substitutes: IngredientSubstitute[];
  substitute_page_slug: string | null;
  storage: string;
  uses: string;
  nutrition_note: string;
  recipe_slugs: string[];
  related_ingredient_slugs: string[];
}

export interface HowToContent {
  hero_image_query: string;
  steps: string[];
  common_mistakes: string[];
  equipment: string[];
  recipe_slugs: string[];
  related_technique_slugs: string[];
}

export interface DefinitionContent {
  hero_image_query: string;
  direct_answer: string;
  expanded_explanation: string;
  usage_origin: string;
  substitute_note: string;
  substitute_page_slug: string | null;
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
  item_a_name: string;
  item_b_name: string;
  comparison_table: ComparisonRow[];
  verdict: string;
  sections: ComparisonSection[];
  item_a_link: LinkRef | null;
  item_b_link: LinkRef | null;
}

export interface RankedSubstitute {
  name: string;
  ratio: string;
  best_for: string;
  note: string;
}

export interface SubstituteContent {
  ranked_substitutes: RankedSubstitute[];
  baking_vs_cooking_note: string;
  hub_page_slug: string | null;
  recipe_slugs: string[];
}

export interface RecipeCardData {
  title: string;
  slug: string | null;
  description: string;
  image_query: string;
}

export interface SubCategory {
  label: string;
  items: string[];
}

export interface CategoryRoundupContent {
  intro: string;
  recipe_cards: RecipeCardData[];
  sub_categories: SubCategory[];
  related_collection_slugs: string[];
}

export interface HomepageContent {
  featured_recipe_slugs: string[];
  category_links: LinkRef[];
  tool_links: LinkRef[];
  positioning_statement: string;
}
