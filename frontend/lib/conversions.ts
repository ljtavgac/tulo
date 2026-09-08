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
