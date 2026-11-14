export function change(amount: number, coins: number[]): number {
  // After processing a prefix of the coins, ways[total] counts the combinations for `total`
  // that use only those coins.
  const ways = new Array<number>(amount + 1).fill(0);
  ways[0] = 1;
  for (const coin of coins) {
    // Increasing totals: ways[total - coin] already allows this coin, so it can repeat.
    for (let total = coin; total <= amount; total++) {
      ways[total] += ways[total - coin];
    }
  }
  return ways[amount];
}
