import Link from "next/link";
import type { ReactNode } from "react";

// Horizontally-scrolling section used to break the homepage into one row
// per template type, rather than the flat stacked grids it had before.
export default function Carousel({
  title,
  seeAllHref,
  children,
}: {
  title: string;
  seeAllHref?: string;
  children: ReactNode;
}) {
  return (
    <section className="mx-auto max-w-6xl px-4 py-6">
      <div className="flex items-baseline justify-between">
        <h2 className="text-xl font-bold">{title}</h2>
        {seeAllHref ? (
          <Link href={seeAllHref} className="text-sm font-semibold text-accent hover:underline">
            See all
          </Link>
        ) : null}
      </div>
      <div className="mt-4 flex snap-x snap-mandatory gap-4 overflow-x-auto pb-2">{children}</div>
    </section>
  );
}
