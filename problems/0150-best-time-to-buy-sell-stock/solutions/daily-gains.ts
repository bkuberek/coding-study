export function maxProfit(prices: number[]): number {
  // A trade from day i to day j earns the sum of the daily changes between them, so the
  // answer is the best sum of a run of consecutive changes (Kadane), or 0.
  let best = 0;
  let endingHere = 0;
  for (let day = 1; day < prices.length; day++) {
    endingHere = Math.max(0, endingHere + prices[day] - prices[day - 1]);
    best = Math.max(best, endingHere);
  }
  return best;
}
