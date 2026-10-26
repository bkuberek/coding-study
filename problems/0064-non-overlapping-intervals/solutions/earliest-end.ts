export function eraseOverlapIntervals(intervals: number[][]): number {
  const byEnd = [...intervals].sort((a, b) => a[1] - b[1]);
  let kept = 0;
  let lastEnd = -Infinity;
  for (const [start, end] of byEnd) {
    if (start >= lastEnd) {
      kept++;
      lastEnd = end;
    }
  }
  return intervals.length - kept;
}
