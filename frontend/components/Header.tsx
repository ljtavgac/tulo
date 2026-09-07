import Link from "next/link";
import Logo from "./Logo";

export default function Header() {
  return (
    <header className="border-b border-ink/10">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/" aria-label="Tulo home">
          <Logo variant="light" className="h-10 w-auto" />
        </Link>
        <nav className="flex items-center gap-5 text-sm font-medium">
          <Link href="/collections/eggplant-recipes" className="hover:text-accent">
            Recipes
          </Link>
          <Link href="/tools/conversion-calculator" className="hover:text-accent">
            Tools
          </Link>
        </nav>
      </div>
    </header>
  );
}
