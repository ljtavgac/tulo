"use client";

import { useMemo, useState } from "react";
import Breadcrumbs from "@/components/Breadcrumbs";
import JsonLd from "@/components/JsonLd";
import FaqSection from "@/components/FaqSection";
import AdSlot from "@/components/AdSlot";
import { absoluteUrl, buildBreadcrumbList } from "@/lib/seo";

const BREADCRUMB_ITEMS = [
  { label: "Home", href: "/" },
  { label: "Food", href: "/food" },
  { label: "Tools", href: "/food/tools" },
  { label: "Cooking Time & Temperature Guide" },
];

const FAQS = [
  {
    question: "What internal temperature is chicken safe to eat at?",
    answer:
      "165°F (74°C) at the thickest part, per USDA guidelines, for both white and dark meat. Dark meat stays tender at that temperature; white meat can dry out if taken much past it.",
  },
  {
    question: "Do I need a meat thermometer, or can I judge doneness by time alone?",
    answer:
      "A thermometer is far more reliable - cook times vary with the exact size and shape of a cut, starting temperature, and your oven or grill's real accuracy. Treat the times in the table as a starting estimate and confirm with a thermometer before serving.",
  },
  {
    question: "Why do these times differ from times I've seen elsewhere?",
    answer:
      "Cook times are inherently approximate - they depend on the exact thickness and starting temperature of what you're cooking, and on how accurate your particular oven, air fryer, or grill actually runs. Always confirm the final internal temperature rather than relying on the clock alone.",
  },
];

const SAFE_MINIMUM_TEMPS: { category: string; temp: string }[] = [
  { category: "Poultry — whole, parts, or ground (chicken, turkey, duck)", temp: "165°F (74°C)" },
  { category: "Ground meat (beef, pork, lamb, veal)", temp: "160°F (71°C)" },
  { category: "Beef, pork, lamb, veal — steaks, roasts, chops", temp: "145°F (63°C), plus a 3-minute rest" },
  { category: "Fish & shellfish", temp: "145°F (63°C), or until opaque and firm" },
  { category: "Egg dishes", temp: "160°F (71°C)" },
  { category: "Leftovers & casseroles (reheating)", temp: "165°F (74°C)" },
];

type Method = "Oven" | "Air Fryer" | "Grill";

interface CookRow {
  protein: string;
  method: Method;
  temp: string;
  time: string;
  internalTemp: string;
}

const COOK_TIMES: CookRow[] = [
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

const PROTEINS = ["All", ...Array.from(new Set(COOK_TIMES.map((r) => r.protein)))];
const METHODS: ("All" | Method)[] = ["All", "Oven", "Air Fryer", "Grill"];

export default function TimeTemperatureGuideClient() {
  const [protein, setProtein] = useState("All");
  const [method, setMethod] = useState<"All" | Method>("All");

  const rows = useMemo(
    () =>
      COOK_TIMES.filter(
        (r) => (protein === "All" || r.protein === protein) && (method === "All" || r.method === method)
      ),
    [protein, method]
  );

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <Breadcrumbs items={BREADCRUMB_ITEMS} />
      <JsonLd data={buildBreadcrumbList(BREADCRUMB_ITEMS)} />
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "WebApplication",
          name: "Cooking Time & Temperature Guide",
          url: absoluteUrl("/food/tools/time-temperature-guide"),
          applicationCategory: "UtilitiesApplication",
          operatingSystem: "Any (web browser)",
          offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
        }}
      />
      <h1 className="mt-4 text-3xl font-bold">Cooking Time &amp; Temperature Guide</h1>
      <p className="mt-3 text-ink/70">
        Two things at once: the food-safety minimums (how hot it needs to get) and the
        practical cook times by method (how long that takes).
      </p>

      <h2 className="mt-8 text-xl font-bold">Safe minimum internal temperatures</h2>
      <table className="mt-3 w-full text-sm">
        <tbody>
          {SAFE_MINIMUM_TEMPS.map((row) => (
            <tr key={row.category} className="border-b border-ink/10">
              <td className="py-2 pr-4 text-ink/70">{row.category}</td>
              <td className="py-2 text-right font-semibold whitespace-nowrap">{row.temp}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="my-8">
        <AdSlot variant="in-content" />
      </div>

      <h2 className="mt-8 text-xl font-bold">Cooking times by method</h2>
      <div className="mt-3 flex flex-wrap gap-3">
        <label className="flex flex-col text-xs font-medium text-ink/60">
          Protein
          <select
            value={protein}
            onChange={(e) => setProtein(e.target.value)}
            className="mt-1 rounded border border-ink/20 px-2 py-1 text-sm"
          >
            {PROTEINS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-xs font-medium text-ink/60">
          Method
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value as "All" | Method)}
            className="mt-1 rounded border border-ink/20 px-2 py-1 text-sm"
          >
            {METHODS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="border-b border-ink/10 text-left text-xs uppercase tracking-wide text-ink/40">
              <th className="py-2 pr-2">Protein</th>
              <th className="py-2 pr-2">Method</th>
              <th className="py-2 pr-2">Temp</th>
              <th className="py-2 pr-2">Time</th>
              <th className="py-2">Internal temp</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-ink/5">
                <td className="py-2 pr-2">{row.protein}</td>
                <td className="py-2 pr-2">{row.method}</td>
                <td className="py-2 pr-2 whitespace-nowrap">{row.temp}</td>
                <td className="py-2 pr-2 whitespace-nowrap">{row.time}</td>
                <td className="py-2">{row.internalTemp}</td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-6 text-center text-ink/50">
                  No matches for that combination.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <FaqSection faqs={FAQS} />
    </main>
  );
}
