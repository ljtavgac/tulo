import { TEMPLATE_ROUTES } from "./seo";

// Config-driven taxonomy: the single source of truth for header/footer nav
// and breadcrumb trails. Adding a future vertical (Home, Auto, Health,
// Finance, Shopping, ...) is additive -- append to VERTICALS and flip
// `active: true` once it has real content -- not a rewrite of nav
// components. Composes path segments from TEMPLATE_ROUTES rather than
// duplicating them.
//
// This is a nav/breadcrumb-visibility mechanism, not evidence the /food/
// URL structure itself is validated for reuse under other verticals --
// launch_plan.md still recommends separate domains when that's decided.

export interface Section {
  key: string;
  label: string;
  templateType: string;
  path: string;
  // Whether this section has a browsable index page (all 8 do).
  hasIndex: boolean;
  // Whether this section gets a tab in the primary header/nav bar. The
  // long-tail sections (Definitions/Comparisons/Substitutes) still have a
  // real index page -- for the footer's Guides column, breadcrumbs, and
  // the homepage carousel's "See all" link -- but aren't promoted to
  // primary nav; they're discovered via cross-links from recipes/
  // ingredients or the footer, not a top-level tab.
  primaryNav: boolean;
}

export interface Vertical {
  key: string;
  label: string;
  path: string;
  active: boolean;
  sections: Section[];
}

export const VERTICALS: Vertical[] = [
  {
    key: "food",
    label: "Food",
    path: "/food",
    active: true,
    sections: [
      { key: "recipes", label: "Recipes", templateType: "recipe_or_dish", path: `/food/${TEMPLATE_ROUTES.recipe_or_dish}`, hasIndex: true, primaryNav: true },
      { key: "ingredients", label: "Ingredients", templateType: "ingredient_hub", path: `/food/${TEMPLATE_ROUTES.ingredient_hub}`, hasIndex: true, primaryNav: true },
      { key: "how-to", label: "How-To", templateType: "howto_technique", path: `/food/${TEMPLATE_ROUTES.howto_technique}`, hasIndex: true, primaryNav: true },
      { key: "collections", label: "Collections", templateType: "category_roundup", path: `/food/${TEMPLATE_ROUTES.category_roundup}`, hasIndex: true, primaryNav: true },
      { key: "tools", label: "Tools", templateType: "tool_page", path: `/food/${TEMPLATE_ROUTES.tool_page}`, hasIndex: true, primaryNav: true },
      { key: "what-is", label: "Definitions", templateType: "definition", path: `/food/${TEMPLATE_ROUTES.definition}`, hasIndex: true, primaryNav: false },
      { key: "comparisons", label: "Comparisons", templateType: "comparison", path: `/food/${TEMPLATE_ROUTES.comparison}`, hasIndex: true, primaryNav: false },
      { key: "substitutes", label: "Substitutes", templateType: "substitute", path: `/food/${TEMPLATE_ROUTES.substitute}`, hasIndex: true, primaryNav: false },
    ],
  },
  // Not built yet -- defined so future verticals are additive. None of
  // these render anywhere until `active` flips to true and real sections
  // are filled in.
  { key: "home", label: "Home", path: "/home", active: false, sections: [] },
  { key: "auto", label: "Auto", path: "/auto", active: false, sections: [] },
  { key: "health", label: "Health", path: "/health", active: false, sections: [] },
  { key: "finance", label: "Finance", path: "/finance", active: false, sections: [] },
  { key: "shopping", label: "Shopping", path: "/shopping", active: false, sections: [] },
];

export const ACTIVE_VERTICALS = VERTICALS.filter((v) => v.active);

// Convenience accessor for the sections nav/footer actually render today.
export const FOOD_SECTIONS = VERTICALS.find((v) => v.key === "food")!.sections;
export const FOOD_INDEX_SECTIONS = FOOD_SECTIONS.filter((s) => s.primaryNav);

export function sectionForTemplate(templateType: string): Section | undefined {
  return FOOD_SECTIONS.find((s) => s.templateType === templateType);
}

// The 3 tool pages are static, hand-built routes, not DB-backed content --
// not meaningfully queryable via listPages() the way template pages are.
// Shared by the tools index page, the homepage's Tools carousel, and the
// footer. `icon` names a ToolIcon variant -- tools aren't photographable
// content, so they get a simple icon instead of a StockPhotoSlot.
export const TOOL_PAGES: { slug: string; title: string; icon: "calculator" | "wand" | "thermometer" }[] = [
  { slug: "conversion-calculator", title: "Conversion Calculator", icon: "calculator" },
  { slug: "recipe-generator", title: "Recipe Generator", icon: "wand" },
  { slug: "time-temperature-guide", title: "Time & Temperature Guide", icon: "thermometer" },
];
