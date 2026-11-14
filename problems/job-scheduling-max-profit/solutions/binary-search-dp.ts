export function jobScheduling(startTime: number[], endTime: number[], profit: number[]): number {
  const order = startTime.map((_, job) => job).sort((a, b) => endTime[a] - endTime[b]);
  const ends = order.map((job) => endTime[job]);
  // best[i] is the most profit from the first i jobs in end-time order.
  const best = new Array<number>(order.length + 1).fill(0);
  for (let i = 0; i < order.length; i++) {
    const job = order[i];
    // Upper bound: how many of the first i jobs end no later than this one starts.
    let low = 0;
    let high = i;
    while (low < high) {
      const middle = (low + high) >> 1;
      if (ends[middle] <= startTime[job]) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    best[i + 1] = Math.max(best[i], profit[job] + best[low]);
  }
  return best[order.length];
}
