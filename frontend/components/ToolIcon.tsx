// Simple inline icons for the 3 tool pages. Tools aren't photographable
// content the way a dish is, so a StockPhotoSlot placeholder box would just
// read as a permanently-broken image slot -- an icon is the honest,
// permanent representation here, not a stand-in for a future photo.
export default function ToolIcon({
  icon,
  className = "h-8 w-8",
}: {
  icon: "calculator" | "wand" | "thermometer";
  className?: string;
}) {
  if (icon === "calculator") {
    return (
      <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
        <rect x="4" y="2" width="16" height="20" rx="2" stroke="currentColor" strokeWidth="1.5" />
        <rect x="7" y="5" width="10" height="4" rx="0.5" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="7.75" cy="13" r="1" fill="currentColor" />
        <circle cx="12" cy="13" r="1" fill="currentColor" />
        <circle cx="16.25" cy="13" r="1" fill="currentColor" />
        <circle cx="7.75" cy="17" r="1" fill="currentColor" />
        <circle cx="12" cy="17" r="1" fill="currentColor" />
        <circle cx="16.25" cy="17" r="1" fill="currentColor" />
      </svg>
    );
  }

  if (icon === "wand") {
    return (
      <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
        <path d="M4 20L15 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M13 4l0.8 2.2L16 7l-2.2 0.8L13 10l-0.8-2.2L10 7l2.2-0.8L13 4z" fill="currentColor" />
        <path d="M19 11l0.5 1.5L21 13l-1.5 0.5L19 15l-0.5-1.5L17 13l1.5-0.5L19 11z" fill="currentColor" />
        <path d="M6 3l0.5 1.5L8 5l-1.5 0.5L6 7l-0.5-1.5L4 5l1.5-0.5L6 3z" fill="currentColor" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <path
        d="M12 3a2 2 0 0 0-2 2v9.17a3.5 3.5 0 1 0 4 0V5a2 2 0 0 0-2-2z"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path d="M12 8v6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="12" cy="16.5" r="1.25" fill="currentColor" />
    </svg>
  );
}
