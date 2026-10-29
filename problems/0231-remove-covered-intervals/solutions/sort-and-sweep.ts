export function removeCoveredIntervals(intervals: number[][]): number {
  // Equal starts: the longer interval comes first, so it covers the shorter ones after it.
  const ordered = [...intervals].sort((a, b) => a[0] - b[0] || b[1] - a[1]);
  let remaining = 0;
  let reach = -1; // the largest end among the intervals already swept
  for (const [, end] of ordered) {
    if (end > reach) {
      remaining++;
      reach = end;
    }
  }
  return remaining;
}
