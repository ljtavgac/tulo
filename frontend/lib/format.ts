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

// Prep/cook/total time is stored in raw minutes, and total_time_minutes
// routinely runs into the hundreds or thousands once a recipe has a real
// inactive step (chilling, marinating, proofing, an overnight ferment, even
// a week-long sourdough starter) -- the recipe's own data is correct in
// those cases (confirmed by scanning the whole corpus: every large gap
// between total and prep+cook traces to a real described inactive step,
// not bad data), but showing it as a bare "1500 min" reads as broken to a
// reader who has no reason to do that division in their head. Converts to
// the coarsest units that keep the number readable, dropping minutes once
// a duration reaches day-scale (a bare few minutes stops mattering next to
// multi-day figures like a 7-day starter).
export function formatDurationMinutes(totalMinutes: number): string {
  const minutes = Math.round(totalMinutes);
  if (minutes < 60) return `${minutes} min`;

  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  const mins = minutes % 60;

  const parts: string[] = [];
  if (days > 0) parts.push(`${days} day${days === 1 ? "" : "s"}`);
  if (hours > 0) parts.push(`${hours} hr`);
  if (mins > 0 && days === 0) parts.push(`${mins} min`);
  return parts.join(" ");
}
