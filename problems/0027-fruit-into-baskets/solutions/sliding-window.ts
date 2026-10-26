export function totalFruit(fruits: number[]): number {
  const inWindow = new Map<number, number>();
  let left = 0;
  let best = 0;
  for (let right = 0; right < fruits.length; right++) {
    inWindow.set(fruits[right], (inWindow.get(fruits[right]) ?? 0) + 1);
    while (inWindow.size > 2) {
      const leaving = fruits[left++];
      const count = inWindow.get(leaving)! - 1;
      if (count === 0) {
        inWindow.delete(leaving);
      } else {
        inWindow.set(leaving, count);
      }
    }
    best = Math.max(best, right - left + 1);
  }
  return best;
}
