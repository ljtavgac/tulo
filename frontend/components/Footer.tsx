import Link from "next/link";
import Logo from "./Logo";

// The footer is a deliberately dark section -- the concrete place the
// dark-background logo variant and cream text get used, per the brand
// spec ("dark mode, footer if dark-themed, or any dark section").
export default function Footer() {
  return (
    <footer className="bg-ink text-cream">
      <div className="mx-auto max-w-5xl px-4 py-10">
        <Logo variant="dark" className="h-9 w-auto" />
        <p className="mt-4 max-w-md text-sm text-cream/70">
          No life story before the recipe. No clutter. Just what you came here for.
        </p>
        <nav className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <Link href="/" className="text-cream/80 hover:text-accent">
            Home
          </Link>
          <Link href="/collections/eggplant-recipes" className="text-cream/80 hover:text-accent">
            Eggplant Recipes
          </Link>
          <Link href="/tools/conversion-calculator" className="text-cream/80 hover:text-accent">
            Conversion Calculator
          </Link>
          <Link href="/tools/time-temperature-guide" className="text-cream/80 hover:text-accent">
            Time &amp; Temp Guide
          </Link>
          <Link href="/tools/recipe-generator" className="text-cream/80 hover:text-accent">
            Recipe Generator
          </Link>
        </nav>
        <p className="mt-8 text-xs text-cream/50">© {new Date().getFullYear()} Tulo</p>
      </div>
    </footer>
  );
}
