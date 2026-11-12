export function pricesAfterRebate(prices: number[]): number[] {
  const paid = [...prices];
  // Slots still waiting for a rebate; their prices rise strictly from bottom to top.
  const waiting: number[] = [];
  for (let slot = 0; slot < prices.length; slot++) {
    while (waiting.length > 0 && prices[waiting[waiting.length - 1]] >= prices[slot]) {
      const earlier = waiting.pop()!;
      paid[earlier] = prices[earlier] - prices[slot];
    }
    waiting.push(slot);
  }
  return paid;
}
