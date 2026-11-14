export function totalFruit(fruits: number[]): number {
  let best = 0;
  for (let start = 0; start < fruits.length; start++) {
    const first = fruits[start];
    let second = -1;
    let end = start;
    while (end < fruits.length) {
      const fruit = fruits[end];
      if (fruit !== first && fruit !== second) {
        if (second !== -1) {
          break;
        }
        second = fruit;
      }
      end++;
    }
    best = Math.max(best, end - start);
  }
  return best;
}
