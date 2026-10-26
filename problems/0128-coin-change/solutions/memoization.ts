export function coinChange(coins: number[], amount: number): number {
  // fewest(x) never exceeds `unreachable`, which stands for "x cannot be paid".
  const unreachable = amount + 1;
  const unknown = -1;
  const memo = new Array<number>(amount + 1).fill(unknown);
  const fewest = (remaining: number): number => {
    if (remaining === 0) {
      return 0;
    }
    if (memo[remaining] === unknown) {
      let best = unreachable;
      for (const coin of coins) {
        if (coin <= remaining) {
          best = Math.min(best, fewest(remaining - coin) + 1);
        }
      }
      memo[remaining] = best;
    }
    return memo[remaining];
  };
  const answer = fewest(amount);
  return answer === unreachable ? -1 : answer;
}
