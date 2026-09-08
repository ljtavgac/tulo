import Link from "next/link";
import { pagePath } from "@/lib/seo";

// Surfaces one of the 3 kitchen tools from inside a content page, where
// it's actually relevant to what someone's reading (e.g. a Conversion
// Calculator link from a recipe) -- previously tools were only reachable
// from the header/footer nav and the homepage/tools index, never from the
// content that would make someone want one.
export default function ToolCallout({
  slug,
  label,
  queryParams,
}: {
  slug: string;
  label: string;
  // Lets a specific piece of content (e.g. "feta cheese" from an
  // Ingredient Hub page) prefill the destination tool's own input --
  // currently only the Recipe Generator's `ingredients` field reads one.
  queryParams?: Record<string, string>;
}) {
  const path = pagePath("tool_page", slug);
  const query = queryParams ? `?${new URLSearchParams(queryParams).toString()}` : "";
  return (
    <p className="mt-6 rounded-lg border border-dashed border-accent/40 bg-accent/5 p-3 text-sm">
      <Link href={`${path}${query}`} className="font-semibold text-accent hover:underline">
        {label} →
      </Link>
    </p>
  );
}
