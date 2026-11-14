export function findAllRecipes(recipes: string[], ingredients: string[][], supplies: string[]): string[] {
  const available = new Set(supplies);
  const prepared: string[] = [];
  let pending = recipes.map((_, i) => i);
  let changed = true;
  while (changed) {
    changed = false;
    const stillPending: number[] = [];
    for (const i of pending) {
      if (ingredients[i].every((item) => available.has(item))) {
        available.add(recipes[i]);
        prepared.push(recipes[i]);
        changed = true;
      } else {
        stillPending.push(i);
      }
    }
    pending = stillPending;
  }
  return prepared;
}
