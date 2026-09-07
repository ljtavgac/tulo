// Placeholder for the Instacart "Shop Ingredients" button. Inert -- no live
// call to instacart_recipe_links.py yet. Requires Instacart API approval
// and structured ingredient data (already have the latter, per the recipe
// content shape) before this can go live.
export default function ShopIngredientsButton() {
  return (
    <button
      type="button"
      disabled
      title="Instacart integration pending API approval — see instacart_recipe_links.py"
      className="inline-flex cursor-not-allowed items-center gap-2 rounded-full border-2 border-dashed border-ink/20 px-4 py-2 text-sm font-medium text-ink/50"
    >
      🛒 Shop Ingredients
    </button>
  );
}
