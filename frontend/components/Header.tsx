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

        {/* basis-full forces this onto its own line right under the logo on
            mobile, as a single horizontally-scrollable row, rather than
            wrapping raggedly across two lines of its own the way flex-wrap
            alone did at narrow widths. sm+ restores the original inline,
            wrapping layout since there's room for it there. */}
        <nav className="flex basis-full flex-nowrap items-center gap-x-6 gap-y-1 overflow-x-auto whitespace-nowrap text-xs font-semibold uppercase tracking-wide text-ink/70 [scrollbar-width:none] sm:basis-auto sm:flex-wrap sm:overflow-visible sm:whitespace-normal [&::-webkit-scrollbar]:hidden">
          {FOOD_INDEX_SECTIONS.map((section) => (
            <Link key={section.key} href={section.path} className="shrink-0 transition-colors hover:text-accent">
              {section.label}
            </Link>
          ))}
        </nav>

        <SearchBox />
      </div>
    </header>
  );
}
