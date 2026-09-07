import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPage } from "@/lib/api";
import type { ComparisonContent } from "@/lib/types";
import { buildPageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const page = await getPage<ComparisonContent>(slug);
  if (!page || page.template_type !== "comparison") return {};
  return buildPageMetadata(page);
}

export default async function ComparisonPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const page = await getPage<ComparisonContent>(slug);
  if (!page || page.template_type !== "comparison") notFound();

  const { content } = page;

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-3xl font-bold">{page.title}</h1>

      <div className="mt-6 overflow-x-auto">
        <table className="w-full border-collapse overflow-hidden rounded-lg border border-ink/10 text-sm">
          <thead>
            <tr className="bg-ink/5 text-left">
              <th className="p-3 font-semibold"> </th>
              <th className="p-3 font-semibold">{content.item_a_name}</th>
              <th className="p-3 font-semibold">{content.item_b_name}</th>
            </tr>
          </thead>
          <tbody>
            {content.comparison_table.map((row) => (
              <tr key={row.attribute} className="border-t border-ink/10">
                <td className="p-3 font-medium text-ink/60">{row.attribute}</td>
                <td className="p-3">{row.item_a}</td>
                <td className="p-3">{row.item_b}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-6 rounded-lg border-l-4 border-accent bg-ink/5 p-4">
        <p className="text-sm font-semibold uppercase tracking-wide text-accent">Verdict</p>
        <p className="mt-1 text-ink/80">{content.verdict}</p>
      </div>

      {content.sections.map((section) => (
        <section key={section.heading} className="mt-8">
          <h2 className="text-xl font-bold">{section.heading}</h2>
          <p className="mt-2 text-ink/80">{section.body}</p>
        </section>
      ))}
    </main>
  );
}
