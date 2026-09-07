// Nearest common cooking fraction, used to keep scaled quantities readable
// (e.g. "1 1/3 cups" rather than "1.3333333333333333 cups").
const FRACTIONS: [number, number][] = [
  [0, 1],
  [1, 8],
  [1, 4],
  [1, 3],
  [3, 8],
  [1, 2],
  [5, 8],
  [2, 3],
  [3, 4],
  [7, 8],
  [1, 1],
];

export function formatUsQuantity(value: number): string {
  if (value <= 0) return "0";
  const whole = Math.floor(value);
  const fracValue = value - whole;

  let best = FRACTIONS[0];
  let bestDiff = Math.abs(fracValue - best[0] / best[1]);
  for (const f of FRACTIONS) {
    const diff = Math.abs(fracValue - f[0] / f[1]);
    if (diff < bestDiff) {
      best = f;
      bestDiff = diff;
    }
  }

  const [num, den] = best;
  if (num === 0) return whole === 0 ? "0" : String(whole);
  if (num === den) return String(whole + 1);
  const fracStr = `${num}/${den}`;
  return whole === 0 ? fracStr : `${whole} ${fracStr}`;
}

export function formatMetricQuantity(value: number): string {
  return String(Math.round(value));
}
