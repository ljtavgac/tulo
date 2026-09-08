import Link from "next/link";
import StockPhotoSlot from "./StockPhotoSlot";
import type { ImageAttribution } from "@/lib/types";

// A photo card for grids of already-resolved pages (section index pages),
// as opposed to RecipeCard, which is specifically for recipe_or_dish links
// (it hardcodes that route) and handles a null slug ("coming soon") for
// slugs mentioned before their page exists -- neither applies here, since
// listPages() only ever returns real, existing pages.
export default function PageTile({
  href,
  title,
  imageQuery,
  imageAlt,
  imageUrl,
  imageAttribution,
}: {
  href: string;
  title: string;
  imageQuery: string;
  imageAlt?: string | null;
  imageUrl?: string;
  imageAttribution?: ImageAttribution;
}) {
  return (
    <Link
      href={href}
      className="block overflow-hidden rounded-card bg-cream shadow-card transition-shadow hover:shadow-lg"
    >
      <StockPhotoSlot
        query={imageQuery}
        alt={imageAlt}
        imageUrl={imageUrl}
        attribution={imageAttribution}
        aspect="thumbnail"
        reserveSpace
        showAttribution={false}
      />
      <div className="p-3">
        <h3 className="line-clamp-2 min-h-10 text-sm font-bold">{title}</h3>
      </div>
    </Link>
  );
}
