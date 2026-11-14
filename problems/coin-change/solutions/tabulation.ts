export function coinChange(coins: number[], amount: number): number {
  // fewest[x] is the fewest coins that pay x exactly; amount + 1 means "cannot be paid".
  const unreachable = amount + 1;
  const fewest = new Array<number>(amount + 1).fill(unreachable);
  fewest[0] = 0;
  for (let x = 1; x <= amount; x++) {
    for (const coin of coins) {
      if (coin <= x && fewest[x - coin] + 1 < fewest[x]) {
        fewest[x] = fewest[x - coin] + 1;
      }
    }
  }
  return fewest[amount] === unreachable ? -1 : fewest[amount];
}
