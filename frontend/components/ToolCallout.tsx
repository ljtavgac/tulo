import Link from "next/link";
import { pagePath } from "@/lib/seo";

// Surfaces one of the 3 kitchen tools from inside a content page, where
// it's actually relevant to what someone's reading (e.g. a Conversion
// Calculator link from a recipe) -- previously tools were only reachable
// from the header/footer nav and the homepage/tools index, never from the
// content that would make someone want one.
export default function ToolCallout({ slug, label }: { slug: string; label: string }) {
  return (
    <p className="mt-6 rounded-lg border border-dashed border-accent/40 bg-accent/5 p-3 text-sm">
      <Link href={pagePath("tool_page", slug)} className="font-semibold text-accent hover:underline">
        {label} →
      </Link>
    </p>
  );
}
