export function insert(intervals: number[][], newInterval: number[]): number[][] {
  const all = [...intervals, newInterval].sort((a, b) => a[0] - b[0]);
  const merged: number[][] = [];
  for (const [start, end] of all) {
    const last = merged[merged.length - 1];
    if (last !== undefined && start <= last[1]) {
      last[1] = Math.max(last[1], end);
    } else {
      merged.push([start, end]);
    }
  }
  return merged;
}
