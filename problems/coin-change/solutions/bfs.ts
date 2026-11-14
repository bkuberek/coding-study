export function coinChange(coins: number[], amount: number): number {
  // Remainders are nodes and paying one coin is an edge; the first level that reaches 0 is
  // the fewest number of coins.
  const seen = new Array<boolean>(amount + 1).fill(false);
  seen[amount] = true;
  let level = [amount];
  let coinsUsed = 0;
  while (level.length > 0) {
    if (seen[0]) {
      return coinsUsed;
    }
    const nextLevel: number[] = [];
    for (const remaining of level) {
      for (const coin of coins) {
        const rest = remaining - coin;
        if (rest >= 0 && !seen[rest]) {
          seen[rest] = true;
          nextLevel.push(rest);
        }
      }
    }
    level = nextLevel;
    coinsUsed++;
  }
  return -1;
}
