export function maxProfit(prices: number[]): number {
  // The three end-of-day states of the previous day: holding a share, just sold, resting.
  let hold = -prices[0];
  let sold = 0;
  let rest = 0;
  for (let i = 1; i < prices.length; i++) {
    [hold, sold, rest] = [Math.max(hold, rest - prices[i]), hold + prices[i], Math.max(rest, sold)];
  }
  return Math.max(sold, rest);
}
