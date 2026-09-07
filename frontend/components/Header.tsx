import Link from "next/link";
import Logo from "./Logo";
import { FOOD_INDEX_SECTIONS } from "@/lib/taxonomy";

export default function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-ink/10 bg-cream/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-3 px-4 py-3">
        <Link href="/food" aria-label="Tulo home" className="shrink-0">
          <Logo variant="light" className="h-[57px] w-auto" />
        </Link>

        <nav className="flex flex-wrap items-center gap-x-6 gap-y-1 text-xs font-semibold uppercase tracking-wide text-ink/70">
          {FOOD_INDEX_SECTIONS.map((section) => (
            <Link key={section.key} href={section.path} className="transition-colors hover:text-accent">
              {section.label}
            </Link>
          ))}
        </nav>

        {/* Not wired to a working /search route yet -- see the homepage's
            note on why no SearchAction structured data is emitted either. */}
        <form
          role="search"
          className="ml-auto flex min-w-[10rem] flex-1 items-center gap-2 rounded-full border border-ink/15 bg-white px-3.5 py-2 sm:flex-none sm:basis-64 focus-within:border-accent"
        >
          <svg aria-hidden viewBox="0 0 20 20" fill="none" className="h-4 w-4 shrink-0 text-ink/40">
            <circle cx="9" cy="9" r="6" stroke="currentColor" strokeWidth="1.5" />
            <path d="M13.5 13.5L17.5 17.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <input
            type="search"
            placeholder="Search recipes…"
            className="w-full bg-transparent text-sm outline-none placeholder:text-ink/40"
          />
        </form>
      </div>
    </header>
  );
}
