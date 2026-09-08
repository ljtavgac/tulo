import type { Metadata } from "next";

const TITLE = "About";
const DESCRIPTION = "What Tulo is and why it's built the way it is.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/about" },
  openGraph: { title: TITLE, description: DESCRIPTION, url: "/about" },
};

export default function AboutPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-bold">About Tulo</h1>

      <div className="mt-6 space-y-4 text-ink/80">
        <p>
          Tulo is a recipe and food-content site built around one idea: the recipe should be
          the first thing you see, not the last thing you scroll to. No life story before the
          ingredients list, no unrelated content mixed in, just the recipe, real information
          about the ingredients in it, and tools that are actually useful while you cook.
        </p>
        <p>
          Every recipe on Tulo comes with live serving-size scaling and US/metric unit
          conversion built directly into the ingredients list, not bolted on as a separate
          calculator. Where the data exists, you can also see how swapping an ingredient
          changes the nutrition, adjust a recipe for a different pan size with the bake time
          recalculated for you, and get plain-language explanations of techniques and
          ingredients linked right from the instructions.
        </p>
        <p>
          Ingredient hubs, how-to guides, substitute comparisons, and curated collections are
          all built to answer the specific question that brought you to the page, not to pad
          out word count. If a page doesn&apos;t have something useful to add, it doesn&apos;t
          get published.
        </p>
        <p>
          Tulo is an independent site, still early and actively growing its library of
          recipes and guides. If something looks wrong, missing, or could be better, we&apos;d
          genuinely like to hear about it &mdash; see the{" "}
          <a href="/contact" className="underline hover:text-accent">
            Contact page
          </a>{" "}
          for how to reach us.
        </p>
      </div>
    </main>
  );
}
