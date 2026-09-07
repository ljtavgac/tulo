"use client";

export type Unit = "us" | "metric";

export default function UnitToggle({
  unit,
  onChange,
}: {
  unit: Unit;
  onChange: (next: Unit) => void;
}) {
  return (
    <div className="flex items-center gap-1 rounded-full border border-ink/20 p-1 text-sm">
      {(["us", "metric"] as const).map((value) => (
        <button
          key={value}
          type="button"
          onClick={() => onChange(value)}
          aria-pressed={unit === value}
          className={`rounded-full px-3 py-1 transition-colors ${
            unit === value ? "bg-ink text-cream" : "hover:text-accent"
          }`}
        >
          {value === "us" ? "US" : "Metric"}
        </button>
      ))}
    </div>
  );
}
