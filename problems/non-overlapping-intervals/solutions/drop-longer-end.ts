export function eraseOverlapIntervals(intervals: number[][]): number {
  const ordered = [...intervals].sort((a, b) => a[0] - b[0]);
  let removed = 0;
  let keptEnd = ordered[0][1];
  for (let i = 1; i < ordered.length; i++) {
    const [start, end] = ordered[i];
    if (start < keptEnd) {
      // Conflict: keep whichever of the two ends first.
      removed++;
      keptEnd = Math.min(keptEnd, end);
    } else {
      keptEnd = end;
    }
  }
  return removed;
}
