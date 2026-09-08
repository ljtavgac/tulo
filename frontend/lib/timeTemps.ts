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
