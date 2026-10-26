export function change(amount: number, coins: number[]): number {
  // ways[i][total] caches the combinations for `total` using coins[i:]; -1 is unknown.
  const ways = Array.from({ length: coins.length }, () => new Array<number>(amount + 1).fill(-1));
  const count = (i: number, total: number): number => {
    if (total === 0) {
      return 1;
    }
    if (i === coins.length) {
      return 0;
    }
    if (ways[i][total] < 0) {
      // Either no coin of value coins[i] is used, or at least one is.
      const skip = count(i + 1, total);
      const use = coins[i] <= total ? count(i, total - coins[i]) : 0;
      ways[i][total] = skip + use;
    }
    return ways[i][total];
  };
  return count(0, amount);
}
