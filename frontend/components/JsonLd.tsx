// Renders a JSON-LD structured-data block. `data` is trusted, server-built
// content (recipe/how-to/page data from our own backend, never raw user
// input), so JSON.stringify is safe to inline here.
export default function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
