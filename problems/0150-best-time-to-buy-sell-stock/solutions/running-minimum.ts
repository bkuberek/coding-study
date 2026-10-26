export function maxProfit(prices: number[]): number {
  let cheapest = prices[0];
  let best = 0;
  for (const price of prices) {
    // Selling today, the best purchase is the cheapest earlier day (or today: profit 0).
    best = Math.max(best, price - cheapest);
    cheapest = Math.min(cheapest, price);
  }
  return best;
}
