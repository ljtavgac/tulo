import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPage } from "@/lib/api";
import type { HowToContent } from "@/lib/types";
import StockPhotoSlot from "@/components/StockPhotoSlot";
import JsonLd from "@/components/JsonLd";
import Breadcrumbs from "@/components/Breadcrumbs";
import FaqSection from "@/components/FaqSection";
import RelatedLinks from "@/components/RelatedLinks";
import ToolCallout from "@/components/ToolCallout";
import AdSlot from "@/components/AdSlot";
import StepTempReference from "@/components/StepTempReference";
import LinkifiedText from "@/components/LinkifiedText";
import { buildBreadcrumbList, buildPageMetadata } from "@/lib/seo";
import { sectionForTemplate } from "@/lib/taxonomy";
import { detectFoodCategory } from "@/lib/timeTemps";
import { getLinkTerms } from "@/lib/linkTerms";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const page = await getPage<HowToContent>(slug);
  if (!page || page.template_type !== "howto_technique") return {};
  return buildPageMetadata(page);
}

export default async function HowToPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const page = await getPage<HowToContent>(slug);
  if (!page || page.template_type !== "howto_technique") notFound();

  const { content } = page;

  const section = sectionForTemplate(page.template_type)!;
  const breadcrumbItems = [
    { label: "Home", href: "/" },
    { label: "Food", href: "/food" },
    { label: section.label, href: section.path },
    { label: page.title },
  ];
  const tempReference = detectFoodCategory([page.title, content.intro, ...content.steps].join(" "));
  const linkTerms = await getLinkTerms(slug);

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <Breadcrumbs items={breadcrumbItems} />
      <JsonLd data={buildBreadcrumbList(breadcrumbItems)} />
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "HowTo",
          name: page.title,
          description: content.meta_description ?? content.intro,
          image: content.image_url,
          step: content.steps.map((step) => ({
            "@type": "HowToStep",
            text: step,
          })),
          // No separate consumables/"supply" field exists in the content
          // model (e.g. brine ingredients) -- equipment items are the ones
          // this site actually has real data for, so only `tool` (HowToTool)
          // is included. Adding a fabricated `supply` list would be worse
          // than omitting it.
          ...(content.equipment.length > 0
            ? { tool: content.equipment.map((item) => ({ "@type": "HowToTool", name: item })) }
            : {}),
        }}
      />
      <h1 className="mt-4 text-3xl font-bold">{page.title}</h1>
      <StockPhotoSlot
        query={content.hero_image_query}
        alt={content.image_alt}
        imageUrl={content.image_url}
        attribution={content.image_attribution}
        className="mt-4"
      />

      <p className="mt-4 text-ink/80">
        <LinkifiedText text={content.intro} terms={linkTerms} />
      </p>

      <h2 className="mt-8 text-xl font-bold">Steps</h2>
      <ol className="mt-3 space-y-3">
        {content.steps.map((step, i) => (
          <li key={i} className="flex gap-3 text-sm">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ink text-xs font-semibold text-cream">
              {i + 1}
            </span>
            <span className="pt-0.5">
              <LinkifiedText text={step} terms={linkTerms} />
              <StepTempReference step={step} reference={tempReference} />
            </span>
          </li>
        ))}
      </ol>

      <AdSlot variant="in-content" />

      <h2 className="mt-8 text-xl font-bold">Common mistakes</h2>
      <ul className="mt-3 space-y-2">
        {content.common_mistakes.map((mistake, i) => (
          <li key={i} className="rounded-lg border border-ink/10 p-3 text-sm text-ink/80">
            {mistake}
          </li>
        ))}
      </ul>

      <h2 className="mt-8 text-xl font-bold">Equipment</h2>
      <ul className="mt-3 flex flex-wrap gap-2">
        {content.equipment.map((item) => (
          <li key={item} className="rounded-full border border-ink/20 px-3 py-1 text-xs">
            {item}
          </li>
        ))}
      </ul>

      <FaqSection faqs={content.faqs} />

      <ToolCallout slug="time-temperature-guide" label="Need exact temperatures or timing? Check our Time & Temperature Guide" />

      <RelatedLinks heading="Recipes using this technique" templateType="recipe_or_dish" slugs={content.recipe_slugs} />

      <RelatedLinks
        heading="Related techniques"
        templateType="howto_technique"
        slugs={content.related_technique_slugs}
      />
    </main>
  );
}
