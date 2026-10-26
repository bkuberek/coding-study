export function candy(ratings: number[]): number {
  const n = ratings.length;
  const candies = new Array<number>(n).fill(1);
  let changed = true;
  while (changed) {
    // Raise any child who does not have more than a lower-rated neighbor; repeat until no
    // rule is violated. Counts only grow, and each raise is the least that fixes it.
    changed = false;
    for (let i = 0; i < n; i++) {
      if (i > 0 && ratings[i] > ratings[i - 1] && candies[i] <= candies[i - 1]) {
        candies[i] = candies[i - 1] + 1;
        changed = true;
      }
      if (i < n - 1 && ratings[i] > ratings[i + 1] && candies[i] <= candies[i + 1]) {
        candies[i] = candies[i + 1] + 1;
        changed = true;
      }
    }
  }
  return candies.reduce((sum, count) => sum + count, 0);
}
