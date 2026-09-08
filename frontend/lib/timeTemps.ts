// Shared with the standalone Time & Temperature Guide tool page
// (app/food/tools/time-temperature-guide) so a contextual reference
// embedded elsewhere (e.g. a recipe step that mentions a doneness check)
// uses the exact same data instead of a second, divergent copy.

export const SAFE_MINIMUM_TEMPS: { category: string; temp: string }[] = [
  { category: "Poultry — whole, parts, or ground (chicken, turkey, duck)", temp: "165°F (74°C)" },
  { category: "Ground meat (beef, pork, lamb, veal)", temp: "160°F (71°C)" },
  { category: "Beef, pork, lamb, veal — steaks, roasts, chops", temp: "145°F (63°C), plus a 3-minute rest" },
  { category: "Fish & shellfish", temp: "145°F (63°C), or until opaque and firm" },
  { category: "Egg dishes", temp: "160°F (71°C)" },
  { category: "Leftovers & casseroles (reheating)", temp: "165°F (74°C)" },
];

export type Method = "Oven" | "Air Fryer" | "Grill";

export interface CookRow {
  protein: string;
  method: Method;
  temp: string;
  time: string;
  internalTemp: string;
}

export const COOK_TIMES: CookRow[] = [
  { protein: "Chicken breast (boneless)", method: "Oven", temp: "400°F", time: "20–25 min", internalTemp: "165°F" },
  { protein: "Chicken breast (boneless)", method: "Air Fryer", temp: "380°F", time: "18–20 min", internalTemp: "165°F" },
  { protein: "Chicken breast (boneless)", method: "Grill", temp: "450°F", time: "6–8 min per side", internalTemp: "165°F" },
  { protein: "Chicken thighs (bone-in)", method: "Oven", temp: "425°F", time: "35–40 min", internalTemp: "165°F" },
  { protein: "Chicken thighs (bone-in)", method: "Air Fryer", temp: "380°F", time: "22–25 min", internalTemp: "165°F" },
  { protein: "Whole chicken (3–4 lb)", method: "Oven", temp: "375°F", time: "~20 min/lb (75–90 min total)", internalTemp: "165°F" },
  { protein: "Salmon fillet", method: "Oven", temp: "400°F", time: "12–15 min", internalTemp: "145°F" },
  { protein: "Salmon fillet", method: "Air Fryer", temp: "400°F", time: "8–10 min", internalTemp: "145°F" },
  { protein: "Burger patties", method: "Grill", temp: "450°F", time: "4–5 min per side", internalTemp: "160°F" },
  { protein: "Steak (1-inch)", method: "Grill", temp: "450–500°F", time: "4–5 min per side", internalTemp: "145°F min (often pulled at 130–135°F for medium-rare)" },
  { protein: "Pork chops (¾-inch, boneless)", method: "Oven", temp: "400°F", time: "12–15 min", internalTemp: "145°F" },
  { protein: "Pork chops (¾-inch, boneless)", method: "Grill", temp: "400°F", time: "4–5 min per side", internalTemp: "145°F" },
  { protein: "Shrimp", method: "Air Fryer", temp: "400°F", time: "6–8 min", internalTemp: "Opaque & firm (145°F)" },
];

// Contextual reference for a doneness/temperature step on a Recipe or
// How-To page. Deliberately matches against SAFE_MINIMUM_TEMPS (a food
// *category*'s safe internal temperature) rather than COOK_TIMES: COOK_TIMES
// rows are specific to Oven/Air Fryer/Grill, but real recipe steps also
// simmer, sear, and boil -- surfacing an Oven time on a step that's actually
// boiling chicken would be confidently wrong. The category-level safe
// minimum holds regardless of method, so it's the one fact that's always
// correct to show.
const CATEGORY_KEYWORDS: { pattern: RegExp; category: string }[] = [
  { pattern: /\b(chicken|turkey|duck|poultry)\b/i, category: "Poultry — whole, parts, or ground (chicken, turkey, duck)" },
  { pattern: /\bground (beef|pork|lamb|veal|meat)\b/i, category: "Ground meat (beef, pork, lamb, veal)" },
  // Deliberately excludes the bare word "roast" -- it's used constantly for
  // vegetables (roasted spaghetti squash, roasted beets) and even coffee
  // roast level, not just meat, so it would wrongly flag those pages as a
  // meat category. "beef"/"pork"/"lamb"/"veal" and named cuts are specific
  // enough to keep.
  { pattern: /\b(steak|pork chop|lamb chop|veal chop|beef|pork|lamb|veal)\b/i, category: "Beef, pork, lamb, veal — steaks, roasts, chops" },
  { pattern: /\b(fish|salmon|shrimp|shellfish|bass|fillet)\b/i, category: "Fish & shellfish" },
  // No bare "egg"/"eggs" pattern here, on purpose -- same class of problem
  // as the excluded "roast" above. "Egg dishes" in SAFE_MINIMUM_TEMPS means
  // an egg-centric dish (omelet, frittata, quiche, custard), but "egg" as a
  // keyword would also match any recipe that merely uses egg as one of
  // several ingredients (a loaf of banana bread, a cocktail's egg-white
  // foam) -- none of which are being cooked to an egg-dish safe minimum.
  // None of this site's current recipes is actually an egg-centric dish, so
  // there's nothing to detect correctly yet; revisit with a more targeted
  // signal (e.g. the page's own title/type) if one is added.
  { pattern: /\b(leftover|reheat|casserole)\b/i, category: "Leftovers & casseroles (reheating)" },
];

// A step only gets a temp reference chip if it actually raises a doneness
// or temperature question -- not just any step in a recipe that happens to
// involve chicken (e.g. "season the chicken breasts with salt"), and not
// every step with a temperature in it (an oven-preheat step like "Preheat
// to 375°F" has a °F in it but isn't a doneness check). Requires both a
// doneness-related word AND a numeric temperature in the same step.
const DONENESS_WORD = /internal|thermometer|cooked through|no longer pink|juices run clear|opaque|safe minimum/i;
const HAS_TEMP_NUMBER = /°[cf]|\d{2,3}\s?degrees/i;
const DONENESS_SIGNAL = { test: (step: string) => DONENESS_WORD.test(step) && HAS_TEMP_NUMBER.test(step) };

// Determines the food category for an entire recipe/how-to page from a
// blob of context text (ingredient names, or title + intro + steps for a
// How-To page, which has no ingredients list). Checked once per page, not
// per step, since a single step rarely repeats the protein's name.
export function detectFoodCategory(contextText: string): { category: string; temp: string } | null {
  for (const { pattern, category } of CATEGORY_KEYWORDS) {
    if (pattern.test(contextText)) {
      return SAFE_MINIMUM_TEMPS.find((row) => row.category === category) ?? null;
    }
  }
  return null;
}

export function stepHasDonenessSignal(step: string): boolean {
  return DONENESS_SIGNAL.test(step);
}
