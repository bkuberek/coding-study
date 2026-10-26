export function maxProfit(prices: number[]): number {
  const n = prices.length;
  // memo[holding][day] is the most profit from `day` on, or -1 when unknown.
  const memo = [new Array<number>(n).fill(-1), new Array<number>(n).fill(-1)];
  const best = (day: number, holding: number): number => {
    if (day >= n) {
      return 0;
    }
    if (memo[holding][day] === -1) {
      const wait = best(day + 1, holding);
      // Selling today forces tomorrow to be a cooldown day, so resume on day + 2.
      const act = holding === 1 ? prices[day] + best(day + 2, 0) : -prices[day] + best(day + 1, 1);
      memo[holding][day] = Math.max(wait, act);
    }
    return memo[holding][day];
  };
  return best(0, 0);
}
