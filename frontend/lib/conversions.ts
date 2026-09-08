// Shared with the standalone Conversion Calculator tool page
// (app/food/tools/conversion-calculator) so an inline conversion embedded
// elsewhere (e.g. a recipe ingredient's unit) uses the exact same numbers
// instead of a second, divergent copy.

// Base unit: milliliters. Ratios are the standard US customary <-> metric
// conversion factors (exact volume-to-volume, no ingredient density
// involved -- see WEIGHT_UNITS for grams/ounces instead).
export const VOLUME_UNITS = {
  teaspoon: 4.92892,
  tablespoon: 14.7868,
  "fluid ounce": 29.5735,
  cup: 236.588,
  pint: 473.176,
  quart: 946.353,
  liter: 1000,
  milliliter: 1,
} as const;

// Base unit: grams.
export const WEIGHT_UNITS = {
  gram: 1,
  kilogram: 1000,
  ounce: 28.3495,
  pound: 453.592,
} as const;

export const GAS_MARKS: { mark: string; fahrenheit: number; celsius: number }[] = [
  { mark: "1", fahrenheit: 275, celsius: 140 },
  { mark: "2", fahrenheit: 300, celsius: 150 },
  { mark: "3", fahrenheit: 325, celsius: 165 },
  { mark: "4", fahrenheit: 350, celsius: 180 },
  { mark: "5", fahrenheit: 375, celsius: 190 },
  { mark: "6", fahrenheit: 400, celsius: 200 },
  { mark: "7", fahrenheit: 425, celsius: 220 },
  { mark: "8", fahrenheit: 450, celsius: 230 },
  { mark: "9", fahrenheit: 475, celsius: 240 },
];

export function round(value: number, decimals = 2): number {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

export type ConversionCategory = "volume" | "weight";

// A recipe ingredient's unit_us is a short, informal string ("tbsp", "cups"),
// not the canonical key VOLUME_UNITS/WEIGHT_UNITS use ("tablespoon", "cup").
// Deliberately excludes "oz": it's genuinely ambiguous between fluid ounce
// (a splash of amaretto) and weight ounce (a block of cream cheese), and
// nothing in the ingredient data says which -- guessing wrong would show a
// confidently incorrect conversion, worse than showing none. Everything
// else here is unambiguous regardless of what it's measuring.
const UNIT_ALIASES: Record<string, { category: ConversionCategory; canonical: string }> = {
  cup: { category: "volume", canonical: "cup" },
  cups: { category: "volume", canonical: "cup" },
  tablespoon: { category: "volume", canonical: "tablespoon" },
  tablespoons: { category: "volume", canonical: "tablespoon" },
  tbsp: { category: "volume", canonical: "tablespoon" },
  teaspoon: { category: "volume", canonical: "teaspoon" },
  teaspoons: { category: "volume", canonical: "teaspoon" },
  tsp: { category: "volume", canonical: "teaspoon" },
  pound: { category: "weight", canonical: "pound" },
  pounds: { category: "weight", canonical: "pound" },
  lb: { category: "weight", canonical: "pound" },
  lbs: { category: "weight", canonical: "pound" },
};

// The handful of target units actually worth showing per category, in
// display order -- not every unit in VOLUME_UNITS (pint/quart/liter are
// rarely useful for a single recipe ingredient's amount).
const DISPLAY_UNITS: Record<ConversionCategory, string[]> = {
  volume: ["teaspoon", "tablespoon", "fluid ounce", "cup", "milliliter"],
  weight: ["ounce", "pound", "gram", "kilogram"],
};

export function getConvertibleUnit(unit: string): { category: ConversionCategory; canonical: string } | null {
  return UNIT_ALIASES[unit.toLowerCase().trim()] ?? null;
}

// `amount` is in `fromUnit` (already the canonical form from
// getConvertibleUnit). Returns the same amount expressed in every other
// unit worth showing for that category.
export function convertToOtherUnits(
  amount: number,
  category: ConversionCategory,
  fromUnit: string
): { unit: string; amount: number }[] {
  const table = category === "volume" ? VOLUME_UNITS : WEIGHT_UNITS;
  const fromRatio = table[fromUnit as keyof typeof table];
  if (fromRatio == null) return [];
  const baseAmount = amount * fromRatio;
  return DISPLAY_UNITS[category]
    .filter((unit) => unit !== fromUnit)
    .map((unit) => ({
      unit,
      amount: round(baseAmount / table[unit as keyof typeof table], unit === "milliliter" || unit === "gram" ? 1 : 2),
    }));
}
