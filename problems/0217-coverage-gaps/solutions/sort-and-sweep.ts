export function coverageGaps(periods: string[][], windowStart: string, windowEnd: string): string[][] {
  // ISO dates compare chronologically as strings; sort a copy, never the caller's array.
  const sorted = [...periods].sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  const gaps: string[][] = [];
  let cursor = windowStart; // every day of the window before cursor is covered or already reported
  for (const [start, end] of sorted) {
    if (cursor >= windowEnd) {
      break;
    }
    if (start > cursor) {
      gaps.push([cursor, start < windowEnd ? start : windowEnd]);
    }
    if (end > cursor) {
      cursor = end;
    }
  }
  if (cursor < windowEnd) {
    gaps.push([cursor, windowEnd]);
  }
  return gaps;
}
