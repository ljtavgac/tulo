import Link from "next/link";
import StockPhotoSlot from "./StockPhotoSlot";
import { pagePath } from "@/lib/seo";
import type { ImageAttribution } from "@/lib/types";

export default function RecipeCard({
  title,
  description,
  imageQuery,
  imageUrl,
  imageAttribution,
  slug,
}: {
  title: string;
  description?: string;
  imageQuery: string;
  imageUrl?: string;
  imageAttribution?: ImageAttribution;
  slug: string | null;
}) {
  const content = (
    <>
      <StockPhotoSlot
        query={imageQuery}
        imageUrl={imageUrl}
        attribution={imageAttribution}
        aspect="thumbnail"
      />
      <div className="p-3">
        <h3 className="text-sm font-bold">{title}</h3>
        {description ? <p className="mt-1 text-xs text-ink/60">{description}</p> : null}
        {!slug ? <p className="mt-1 text-xs italic text-ink/40">Recipe page coming soon</p> : null}
      </div>
    </>
  );

  const cardClass = "block overflow-hidden rounded-card bg-cream shadow-card transition-shadow";

  if (slug) {
    return (
      <Link href={pagePath("recipe_or_dish", slug)} className={`${cardClass} hover:shadow-lg`}>
        {content}
      </Link>
    );
  }

  return <div className={cardClass}>{content}</div>;
}
