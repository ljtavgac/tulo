"use client";

export default function ServingsScaler({
  servings,
  onChange,
}: {
  servings: number;
  onChange: (next: number) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium">Servings</span>
      <button
        type="button"
        onClick={() => onChange(Math.max(1, servings - 1))}
        className="flex h-7 w-7 items-center justify-center rounded-full border border-ink/20 text-sm leading-none hover:border-accent hover:text-accent"
        aria-label="Decrease servings"
      >
        −
      </button>
      <span className="w-6 text-center text-sm font-semibold" aria-live="polite">
        {servings}
      </span>
      <button
        type="button"
        onClick={() => onChange(servings + 1)}
        className="flex h-7 w-7 items-center justify-center rounded-full border border-ink/20 text-sm leading-none hover:border-accent hover:text-accent"
        aria-label="Increase servings"
      >
        +
      </button>
    </div>
  );
}
