import Link from "next/link";
import Logo from "./Logo";
import { FOOD_INDEX_SECTIONS } from "@/lib/taxonomy";

export default function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-ink/10 bg-cream/95 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/food" aria-label="Tulo home">
          <Logo variant="light" className="h-16 w-auto" />
        </Link>
        <nav className="flex items-center gap-5 text-sm font-medium">
          {FOOD_INDEX_SECTIONS.map((section) => (
            <Link key={section.key} href={section.path} className="hover:text-accent">
              {section.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
