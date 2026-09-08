import { getSeasonality } from "@/lib/seasonality";

// Renders nothing for a hub with no real season (see seasonality.ts) --
// omitting the badge entirely is more correct than showing a season for
// every ingredient regardless of whether one actually exists.
export default function InSeasonBadge({ slug }: { slug: string }) {
  const seasonality = getSeasonality(slug);
  if (!seasonality) return null;

  const currentMonth = new Date().getMonth() + 1;
  const inSeason = seasonality.months.includes(currentMonth);

  return (
    <p className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-ink/15 px-3 py-1 text-xs">
      {inSeason ? (
        <span className="font-medium text-accent">● In season now</span>
      ) : (
        <span className="text-ink/50">Peak season: {seasonality.label}</span>
      )}
    </p>
  );
}
