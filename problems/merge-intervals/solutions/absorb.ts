export function merge(intervals: number[][]): number[][] {
  let merged: number[][] = [];
  for (const [first, last] of intervals) {
    let start = first;
    let end = last;
    // Fold every merged interval that shares a point with [start, end] into it.
    const separate: number[][] = [];
    for (const [otherStart, otherEnd] of merged) {
      if (otherStart <= end && start <= otherEnd) {
        start = Math.min(start, otherStart);
        end = Math.max(end, otherEnd);
      } else {
        separate.push([otherStart, otherEnd]);
      }
    }
    separate.push([start, end]);
    merged = separate;
  }
  return merged;
}
