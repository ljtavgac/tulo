"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";

// Horizontally-scrolling section used to break the homepage into one row
// per template type. A client component (not the plain server component it
// started as) so it can track scroll position and offer arrow buttons for
// paging through a row, in addition to native touch/trackpad scrolling.
export default function Carousel({
  title,
  seeAllHref,
  children,
}: {
  title: string;
  seeAllHref?: string;
  children: ReactNode;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  function updateScrollState() {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 4);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 4);
  }

  useEffect(() => {
    updateScrollState();
    window.addEventListener("resize", updateScrollState);
    return () => window.removeEventListener("resize", updateScrollState);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function scrollByPage(direction: 1 | -1) {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollBy({ left: direction * el.clientWidth * 0.85, behavior: "smooth" });
  }

  return (
    <section className="mx-auto max-w-6xl px-4 py-6">
      <div className="flex items-baseline justify-between">
        <h2 className="text-xl font-bold">{title}</h2>
        {seeAllHref ? (
          <Link
            href={seeAllHref}
            className="flex items-center gap-1 rounded-full border border-ink/15 px-3 py-1 text-xs font-semibold text-ink/70 transition-colors hover:border-accent hover:text-accent"
          >
            See all
            <svg viewBox="0 0 20 20" fill="none" className="h-3 w-3" aria-hidden>
              <path d="M7 4l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </Link>
        ) : null}
      </div>

      <div className="relative mt-4">
        <div
          ref={scrollRef}
          onScroll={updateScrollState}
          className="flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-smooth pb-2"
        >
          {children}
        </div>

        {canScrollLeft ? (
          <button
            type="button"
            aria-label="Scroll left"
            onClick={() => scrollByPage(-1)}
            className="absolute left-0 top-1/2 hidden -translate-x-1/2 -translate-y-1/2 rounded-full bg-cream p-2 text-ink shadow-card ring-1 ring-ink/10 transition-colors hover:text-accent sm:flex"
          >
            <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4" aria-hidden>
              <path d="M12 4l-6 6 6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        ) : null}

        {canScrollRight ? (
          <button
            type="button"
            aria-label="Scroll right"
            onClick={() => scrollByPage(1)}
            className="absolute right-0 top-1/2 hidden translate-x-1/2 -translate-y-1/2 rounded-full bg-cream p-2 text-ink shadow-card ring-1 ring-ink/10 transition-colors hover:text-accent sm:flex"
          >
            <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4" aria-hidden>
              <path d="M8 4l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        ) : null}
      </div>
    </section>
  );
}
