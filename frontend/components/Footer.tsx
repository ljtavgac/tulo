import Link from "next/link";
import Logo from "./Logo";
import { FOOD_INDEX_SECTIONS, FOOD_SECTIONS, TOOL_PAGES } from "@/lib/taxonomy";
import { pagePath } from "@/lib/seo";

// The footer is a deliberately dark section -- the concrete place the
// dark-background logo variant and cream text get used, per the brand
// spec ("dark mode, footer if dark-themed, or any dark section"). bg-ink
// (#1f1e1c) rather than pure black: the dark logo PNG has that exact color
// baked into its background, so pure black left a visible seam around it.
// --color-ink is shared with body text/borders elsewhere, but using the
// *token* here (not redefining its value) doesn't touch those.
const LONG_TAIL_SECTIONS = FOOD_SECTIONS.filter((s) => !s.primaryNav);

export default function Footer() {
  return (
    <footer className="bg-ink text-cream">
      <div className="mx-auto grid max-w-5xl gap-10 px-4 py-12 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2 lg:col-span-1">
          <Logo variant="dark" className="h-[62px] w-auto" />
          <p className="mt-4 max-w-xs text-sm text-cream/70">
            Made for you.
          </p>
        </div>

        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-cream/50">Explore</h2>
          <nav className="mt-4 flex flex-col gap-2 text-sm">
            {FOOD_INDEX_SECTIONS.map((section) => (
              <Link key={section.key} href={section.path} className="text-cream/80 hover:text-accent">
                {section.label}
              </Link>
            ))}
          </nav>
        </div>

        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-cream/50">Guides</h2>
          <nav className="mt-4 flex flex-col gap-2 text-sm">
            {LONG_TAIL_SECTIONS.map((section) => (
              <Link key={section.key} href={section.path} className="text-cream/80 hover:text-accent">
                {section.label}
              </Link>
            ))}
          </nav>
        </div>

        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-cream/50">Tools</h2>
          <nav className="mt-4 flex flex-col gap-2 text-sm">
            {TOOL_PAGES.map((tool) => (
              <Link key={tool.slug} href={pagePath("tool_page", tool.slug)} className="text-cream/80 hover:text-accent">
                {tool.title}
              </Link>
            ))}
          </nav>
        </div>
      </div>
      <div className="border-t border-cream/10">
        <p className="mx-auto max-w-5xl px-4 py-6 text-xs text-cream/50">© {new Date().getFullYear()} Tulo</p>
      </div>
    </footer>
  );
}
