export function findAllRecipes(recipes: string[], ingredients: string[][], supplies: string[]): string[] {
  const usedBy = new Map<string, number[]>();
  ingredients.forEach((items, i) => {
    for (const item of items) {
      const users = usedBy.get(item);
      if (users === undefined) {
        usedBy.set(item, [i]);
      } else {
        users.push(i);
      }
    }
  });
  const missing = ingredients.map((items) => items.length); // ingredients each recipe still lacks
  // An array with a moving head is a queue without the O(n) cost of shift().
  const available = [...supplies];
  const prepared: string[] = [];
  for (let head = 0; head < available.length; head++) {
    for (const i of usedBy.get(available[head]) ?? []) {
      missing[i]--;
      if (missing[i] === 0) {
        prepared.push(recipes[i]);
        available.push(recipes[i]);
      }
    }
  }
  return prepared;
}
