export function insert(intervals: number[][], newInterval: number[]): number[][] {
  let [start, end] = newInterval;
  // Separate sorted intervals have increasing starts and increasing ends.
  const first = firstIndex(intervals, (interval) => interval[1] >= start);
  const after = firstIndex(intervals, (interval) => interval[0] > end);
  if (first < after) {
    start = Math.min(start, intervals[first][0]);
    end = Math.max(end, intervals[after - 1][1]);
  }
  return [...intervals.slice(0, first), [start, end], ...intervals.slice(after)];
}

function firstIndex(intervals: number[][], isPast: (interval: number[]) => boolean): number {
  let low = 0;
  let high = intervals.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (isPast(intervals[middle])) {
      high = middle;
    } else {
      low = middle + 1;
    }
  }
  return low;
}
