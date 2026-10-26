export function jobScheduling(startTime: number[], endTime: number[], profit: number[]): number {
  const n = startTime.length;
  const order = startTime.map((_, job) => job).sort((a, b) => startTime[a] - startTime[b]);
  const starts = order.map((job) => startTime[job]);
  // The first position at or after `from` whose start is >= time (starts are sorted).
  const firstStartingAt = (time: number, from: number): number => {
    let low = from;
    let high = n;
    while (low < high) {
      const middle = (low + high) >> 1;
      if (starts[middle] < time) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    return low;
  };
  // memo[index] is the most profit from the jobs at sorted positions index..n-1, or -1.
  const memo = new Array<number>(n).fill(-1);
  const bestFrom = (index: number): number => {
    if (index === n) {
      return 0;
    }
    if (memo[index] === -1) {
      const job = order[index];
      const following = firstStartingAt(endTime[job], index + 1);
      memo[index] = Math.max(bestFrom(index + 1), profit[job] + bestFrom(following));
    }
    return memo[index];
  };
  return bestFrom(0);
}
