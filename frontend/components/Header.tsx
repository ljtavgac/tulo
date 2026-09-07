import Link from "next/link";
import Logo from "./Logo";
import SearchBox from "./SearchBox";
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

        <SearchBox />
      </div>
    </header>
  );
}
