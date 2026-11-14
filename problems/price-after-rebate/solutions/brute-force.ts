export function pricesAfterRebate(prices: number[]): number[] {
  const paid = [...prices];
  for (let slot = 0; slot < prices.length; slot++) {
    for (let later = slot + 1; later < prices.length; later++) {
      if (prices[later] <= prices[slot]) {
        paid[slot] = prices[slot] - prices[later];
        break;
      }
    }
  }
  return paid;
}
