"use client";

// A plain window.print() is genuinely enough for "Print / PDF" -- every
// major browser's print dialog offers "Save as PDF" as a destination, so
// there's no separate PDF generation to build.
export default function PrintButton() {
  return (
    <button
      type="button"
      onClick={() => window.print()}
      className="rounded-full border border-ink/20 px-4 py-2 text-sm font-medium hover:border-accent hover:text-accent"
    >
      🖨️ Print / PDF
    </button>
  );
}
