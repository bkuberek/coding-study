export function jobScheduling(startTime: number[], endTime: number[], profit: number[]): number {
  const order = startTime.map((_, job) => job).sort((a, b) => endTime[a] - endTime[b]);
  // best[i] is the most profit from the first i jobs in end-time order.
  const best = new Array<number>(order.length + 1).fill(0);
  for (let i = 0; i < order.length; i++) {
    const job = order[i];
    // Walk back to the last job that ends no later than this one starts.
    let compatible = i - 1;
    while (compatible >= 0 && endTime[order[compatible]] > startTime[job]) {
      compatible--;
    }
    best[i + 1] = Math.max(best[i], profit[job] + best[compatible + 1]);
  }
  return best[order.length];
}
