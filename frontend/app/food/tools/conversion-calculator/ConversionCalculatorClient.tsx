"use client";

import { useState } from "react";
import Breadcrumbs from "@/components/Breadcrumbs";
import JsonLd from "@/components/JsonLd";
import FaqSection from "@/components/FaqSection";
import AdSlot from "@/components/AdSlot";
import { absoluteUrl, buildBreadcrumbList } from "@/lib/seo";
import { GAS_MARKS, VOLUME_UNITS, WEIGHT_UNITS, round } from "@/lib/conversions";

const BREADCRUMB_ITEMS = [
  { label: "Home", href: "/" },
  { label: "Food", href: "/food" },
  { label: "Tools", href: "/food/tools" },
  { label: "Kitchen Measurement Conversion Calculator" },
];

const FAQS = [
  {
    question: "How many grams are in a cup?",
    answer:
      "It depends entirely on what's in the cup - a cup of flour, a cup of sugar, and a cup of water all weigh different amounts, since a cup measures volume, not weight. Use the weight tab above with the specific ingredient's known conversion rather than one universal number.",
  },
  {
    question: "How do I convert an oven temperature for a fan (convection) oven?",
    answer:
      "A common rule of thumb is to lower the recipe's stated temperature by 25°F (about 15°C) when using a fan/convection oven, since the moving air cooks food faster at the same set temperature. Check times a few minutes early the first time you try it.",
  },
  {
    question: "Is this calculator accurate for every ingredient?",
    answer:
      "The volume and weight conversions are standard, exact unit-to-unit conversions (cups to milliliters, ounces to grams). They don't account for ingredient density, so a cup-to-gram conversion for a specific ingredient (flour, sugar, butter) can differ from these generic unit conversions - check the ingredient's own recipe page for that.",
  },
];

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

export default function ConversionCalculatorClient() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <Breadcrumbs items={BREADCRUMB_ITEMS} />
      <JsonLd data={buildBreadcrumbList(BREADCRUMB_ITEMS)} />
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "WebApplication",
          name: "Kitchen Measurement Conversion Calculator",
          url: absoluteUrl("/food/tools/conversion-calculator"),
          applicationCategory: "UtilitiesApplication",
          operatingSystem: "Any (web browser)",
          offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
        }}
      />
      <h1 className="mt-4 text-3xl font-bold">Kitchen Measurement Conversion Calculator</h1>
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

      <AdSlot variant="in-content" />

      <h2 className="mt-8 text-xl font-bold">Oven Temperature</h2>
      <div className="mt-3">
        <OvenTempConverter />
      </div>

      <FaqSection faqs={FAQS} />
    </main>
  );
}
