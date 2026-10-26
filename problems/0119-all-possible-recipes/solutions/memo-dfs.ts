type Verdict = "on path" | boolean;

export function findAllRecipes(recipes: string[], ingredients: string[][], supplies: string[]): string[] {
  const needs = new Map<string, string[]>(recipes.map((recipe, i) => [recipe, ingredients[i]]));
  const stocked = new Set(supplies);
  // Memo per recipe: true or false once decided, "on path" while it is being explored.
  const verdict = new Map<string, Verdict>();
  const canPrepare = (item: string): boolean => {
    if (stocked.has(item)) {
      return true;
    }
    const items = needs.get(item);
    if (items === undefined) {
      return false; // neither a supply nor a recipe
    }
    const known = verdict.get(item);
    if (known === "on path") {
      return false; // the ingredients loop back to this recipe
    }
    if (known !== undefined) {
      return known;
    }
    verdict.set(item, "on path");
    const result = items.every(canPrepare);
    verdict.set(item, result);
    return result;
  };
  return recipes.filter(canPrepare);
}
