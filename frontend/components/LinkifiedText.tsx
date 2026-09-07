import Link from "next/link";
import type { ReactNode } from "react";
import type { LinkTerm } from "@/lib/linkTerms";

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Auto-links the first mention of each known page name inside a block of
// prose -- e.g. "chives" inside a recipe's description becomes a link to
// the Chives ingredient page, if that page exists. Longer names are
// matched before names they contain (so a two-word ingredient isn't
// pre-empted by a shorter unrelated match), matches require word
// boundaries (so "egg" doesn't match inside "eggplant"), and each term
// links only once even if it's mentioned again later in the same text --
// repeated auto-linking of every mention reads as spammy and adds no
// further SEO value over linking it once.
export default function LinkifiedText({ text, terms }: { text: string; terms: LinkTerm[] }) {
  if (!text || terms.length === 0) return <>{text}</>;

  const sorted = [...terms].sort((a, b) => b.name.length - a.name.length);
  const nodes: ReactNode[] = [];
  let remaining = text;
  const linked = new Set<string>();
  let key = 0;

  while (remaining.length > 0) {
    let earliest: { index: number; term: LinkTerm; length: number } | null = null;

    for (const term of sorted) {
      const lower = term.name.toLowerCase();
      if (linked.has(lower)) continue;
      const match = new RegExp(`\\b${escapeRegExp(term.name)}\\b`, "i").exec(remaining);
      if (match && (earliest === null || match.index < earliest.index)) {
        earliest = { index: match.index, term, length: match[0].length };
      }
    }

    if (!earliest) {
      nodes.push(remaining);
      break;
    }

    if (earliest.index > 0) nodes.push(remaining.slice(0, earliest.index));
    const matchedText = remaining.slice(earliest.index, earliest.index + earliest.length);
    nodes.push(
      <Link
        key={key++}
        href={earliest.term.href}
        className="underline decoration-dotted underline-offset-2 hover:text-accent hover:decoration-solid"
      >
        {matchedText}
      </Link>
    );
    linked.add(earliest.term.name.toLowerCase());
    remaining = remaining.slice(earliest.index + earliest.length);
  }

  return <>{nodes}</>;
}
