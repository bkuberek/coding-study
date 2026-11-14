export function change(amount: number, coins: number[]): number {
  // ways[i][total] is the number of combinations for `total` using only coins[:i].
  const ways = Array.from({ length: coins.length + 1 }, () => new Array<number>(amount + 1).fill(0));
  ways[0][0] = 1;
  for (let i = 1; i <= coins.length; i++) {
    const coin = coins[i - 1];
    for (let total = 0; total <= amount; total++) {
      // Combinations without this coin, plus those that use it at least once.
      ways[i][total] = ways[i - 1][total] + (total >= coin ? ways[i][total - coin] : 0);
    }
  }
  return ways[coins.length][amount];
}
