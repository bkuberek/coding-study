export function totalFruit(fruits: number[]): number {
  let best = 0;
  let window = 0;
  let last = -1;
  let beforeLast = -1;
  let lastRun = 0;
  for (const fruit of fruits) {
    window = fruit === last || fruit === beforeLast ? window + 1 : lastRun + 1;
    if (fruit === last) {
      lastRun++;
    } else {
      beforeLast = last;
      last = fruit;
      lastRun = 1;
    }
    best = Math.max(best, window);
  }
  return best;
}
