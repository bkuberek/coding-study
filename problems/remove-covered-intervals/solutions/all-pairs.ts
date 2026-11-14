export function removeCoveredIntervals(intervals: number[][]): number {
  let remaining = 0;
  for (let i = 0; i < intervals.length; i++) {
    const [start, end] = intervals[i];
    // The interval itself would cover itself, so skip j === i.
    const covered = intervals.some(
      ([otherStart, otherEnd], j) => j !== i && otherStart <= start && end <= otherEnd,
    );
    if (!covered) {
      remaining++;
    }
  }
  return remaining;
}
