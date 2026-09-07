"use client";

import { useState } from "react";

// Base unit: milliliters. Ratios are the standard US customary <-> metric
// conversion factors (exact volume-to-volume, no ingredient density
// involved -- see the weight tab for grams/ounces instead).
const VOLUME_UNITS = {
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
const WEIGHT_UNITS = {
  gram: 1,
  kilogram: 1000,
  ounce: 28.3495,
  pound: 453.592,
} as const;

const GAS_MARKS: { mark: string; fahrenheit: number; celsius: number }[] = [
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

function round(value: number, decimals = 2): number {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

function UnitConverter<U extends string>({
  units,
  defaultFrom,
  defaultTo,
}: {
  units: Record<U, number>;
  defaultFrom: U;
  defaultTo: U;
}) {
  const [amount, setAmount] = useState("1");
  const [from, setFrom] = useState<U>(defaultFrom);
  const [to, setTo] = useState<U>(defaultTo);

  const numericAmount = parseFloat(amount);
  const result =
    Number.isFinite(numericAmount) ? round((numericAmount * units[from]) / units[to], 4) : null;

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-lg border border-ink/10 p-4">
      <label className="flex flex-col text-xs font-medium text-ink/60">
        Amount
        <input
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="mt-1 w-24 rounded border border-ink/20 px-2 py-1 text-sm"
        />
      </label>
      <label className="flex flex-col text-xs font-medium text-ink/60">
        From
        <select
          value={from}
          onChange={(e) => setFrom(e.target.value as U)}
          className="mt-1 rounded border border-ink/20 px-2 py-1 text-sm capitalize"
        >
          {Object.keys(units).map((u) => (
            <option key={u} value={u}>
              {u}
            </option>
          ))}
        </select>
      </label>
      <span className="pb-1.5 text-ink/40">→</span>
      <label className="flex flex-col text-xs font-medium text-ink/60">
        To
        <select
          value={to}
          onChange={(e) => setTo(e.target.value as U)}
          className="mt-1 rounded border border-ink/20 px-2 py-1 text-sm capitalize"
        >
          {Object.keys(units).map((u) => (
            <option key={u} value={u}>
              {u}
            </option>
          ))}
        </select>
      </label>
      <p className="pb-1.5 text-lg font-semibold">
        {result === null ? "—" : `${result} ${to}${result === 1 ? "" : "s"}`}
      </p>
    </div>
  );
}

function OvenTempConverter() {
  const [fahrenheit, setFahrenheit] = useState("350");
  const f = parseFloat(fahrenheit);
  const c = Number.isFinite(f) ? round(((f - 32) * 5) / 9, 0) : null;

  return (
    <div className="rounded-lg border border-ink/10 p-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col text-xs font-medium text-ink/60">
          °Fahrenheit
          <input
            type="number"
            value={fahrenheit}
            onChange={(e) => setFahrenheit(e.target.value)}
            className="mt-1 w-24 rounded border border-ink/20 px-2 py-1 text-sm"
          />
        </label>
        <span className="pb-1.5 text-ink/40">→</span>
        <p className="pb-1.5 text-lg font-semibold">{c === null ? "—" : `${c}°C`}</p>
      </div>

      <table className="mt-4 w-full text-sm">
        <thead>
          <tr className="border-b border-ink/10 text-left text-xs uppercase tracking-wide text-ink/40">
            <th className="py-1">Gas mark</th>
            <th className="py-1">°F</th>
            <th className="py-1">°C</th>
          </tr>
        </thead>
        <tbody>
          {GAS_MARKS.map((row) => (
            <tr key={row.mark} className="border-b border-ink/5">
              <td className="py-1">{row.mark}</td>
              <td className="py-1">{row.fahrenheit}</td>
              <td className="py-1">{row.celsius}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ConversionCalculatorPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-3xl font-bold">Kitchen Measurement Conversion Calculator</h1>
      <p className="mt-3 text-ink/70">
        Convert between US customary and metric kitchen measurements. This tool is also
        embeddable on Recipe pages for converting a specific ingredient on the fly.
      </p>

      <h2 className="mt-8 text-xl font-bold">Volume</h2>
      <div className="mt-3">
        <UnitConverter units={VOLUME_UNITS} defaultFrom="cup" defaultTo="milliliter" />
      </div>

      <h2 className="mt-8 text-xl font-bold">Weight</h2>
      <div className="mt-3">
        <UnitConverter units={WEIGHT_UNITS} defaultFrom="ounce" defaultTo="gram" />
      </div>

      <h2 className="mt-8 text-xl font-bold">Oven Temperature</h2>
      <div className="mt-3">
        <OvenTempConverter />
      </div>
    </main>
  );
}
