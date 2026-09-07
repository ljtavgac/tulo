import Link from "next/link";
import StockPhotoSlot from "./StockPhotoSlot";

export default function RecipeCard({
  title,
  description,
  imageQuery,
  slug,
}: {
  title: string;
  description?: string;
  imageQuery: string;
  slug: string | null;
}) {
  const content = (
    <>
      <StockPhotoSlot query={imageQuery} aspect="thumbnail" />
      <div className="p-3">
        <h3 className="text-sm font-semibold">{title}</h3>
        {description ? <p className="mt-1 text-xs text-ink/60">{description}</p> : null}
        {!slug ? <p className="mt-1 text-xs italic text-ink/40">Recipe page coming soon</p> : null}
      </div>
    </>
  );

  const cardClass = "block overflow-hidden rounded-lg border border-ink/10";

  if (slug) {
    return (
      <Link href={`/recipes/${slug}`} className={`${cardClass} hover:border-accent`}>
        {content}
      </Link>
    );
  }

  return <div className={cardClass}>{content}</div>;
}
