export function candy(ratings: number[]): number {
  const n = ratings.length;
  const candies = new Array<number>(n).fill(1);
  // Left to right: the fewest candies that respect every left neighbor.
  for (let i = 1; i < n; i++) {
    if (ratings[i] > ratings[i - 1]) {
      candies[i] = candies[i - 1] + 1;
    }
  }
  // Right to left: also respect every right neighbor, without undoing the first pass.
  for (let i = n - 2; i >= 0; i--) {
    if (ratings[i] > ratings[i + 1]) {
      candies[i] = Math.max(candies[i], candies[i + 1] + 1);
    }
  }
  return candies.reduce((sum, count) => sum + count, 0);
}
