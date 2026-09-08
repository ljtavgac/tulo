"use client";

import { useState } from "react";

// A collapsed-by-default "why this works" explanation under a recipe step
// that has one. Kept collapsed so a reader who just wants the steps isn't
// forced to scroll past technique explanations they didn't ask for.
export default function StepWhyNote({ note }: { note: string }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="text-xs font-medium text-accent hover:underline"
      >
        {open ? "Hide why" : "Why this works"}
      </button>
      {open ? <p className="mt-1 text-xs text-ink/60">{note}</p> : null}
    </div>
  );
}
