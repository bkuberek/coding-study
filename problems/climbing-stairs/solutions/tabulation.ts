export function climbStairs(n: number): number {
  // ways[step] counts the move sequences that end exactly on `step`.
  const ways = new Array<number>(n + 1).fill(0);
  ways[0] = 1;
  ways[1] = 1;
  for (let step = 2; step <= n; step++) {
    ways[step] = ways[step - 1] + ways[step - 2];
  }
  return ways[n];
}
