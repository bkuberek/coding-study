export function minInterval(intervals: number[][], queries: number[]): number[] {
  return queries.map((query) => {
    let best = Infinity;
    for (const [left, right] of intervals) {
      if (left <= query && query <= right) {
        best = Math.min(best, right - left + 1);
      }
    }
    return best === Infinity ? -1 : best;
  });
}
