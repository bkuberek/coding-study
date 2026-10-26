export function eraseOverlapIntervals(intervals: number[][]): number {
  const ordered = [...intervals].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  // longest[i]: the most intervals that can be kept among ordered[0..i], ending with ordered[i].
  const longest: number[] = [];
  let kept = 0;
  for (let i = 0; i < ordered.length; i++) {
    let best = 0;
    for (let j = 0; j < i; j++) {
      if (ordered[j][1] <= ordered[i][0] && longest[j] > best) {
        best = longest[j];
      }
    }
    longest.push(best + 1);
    kept = Math.max(kept, best + 1);
  }
  return intervals.length - kept;
}
