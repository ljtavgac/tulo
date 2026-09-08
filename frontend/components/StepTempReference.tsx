import { stepHasDonenessSignal } from "@/lib/timeTemps";

// A small contextual note under a Recipe/How-To step that mentions a
// doneness or temperature check -- surfaces the food category's USDA safe
// minimum internal temperature right on the step, not just via a footer
// link to the Time & Temperature Guide. `reference` is computed once per
// page (see detectFoodCategory) and reused across all steps; this
// component only decides whether *this* step is the kind that should show
// it.
export default function StepTempReference({
  step,
  reference,
}: {
  step: string;
  reference: { category: string; temp: string } | null;
}) {
  if (!reference || !stepHasDonenessSignal(step)) return null;

  return (
    <span className="mt-1 block w-fit rounded bg-accent/10 px-2 py-1 text-xs text-ink/70">
      USDA safe minimum for {reference.category.split("—")[0].trim().toLowerCase()}:{" "}
      <span className="font-semibold text-ink">{reference.temp}</span>
    </span>
  );
}
