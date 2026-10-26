export function minWindow(s: string, t: string): string {
  const deficit = new Int32Array(128);
  for (let i = 0; i < t.length; i++) {
    deficit[t.charCodeAt(i)]++;
  }
  const useful: number[] = [];
  for (let i = 0; i < s.length; i++) {
    if (deficit[s.charCodeAt(i)] > 0) {
      useful.push(i);
    }
  }
  let missing = t.length;
  let bestStart = 0;
  let bestLength = 0;
  let left = 0;
  for (const right of useful) {
    if (deficit[s.charCodeAt(right)]-- > 0) {
      missing--;
    }
    while (missing === 0) {
      const start = useful[left];
      if (bestLength === 0 || right - start + 1 < bestLength) {
        bestStart = start;
        bestLength = right - start + 1;
      }
      if (++deficit[s.charCodeAt(start)] > 0) {
        missing++;
      }
      left++;
    }
  }
  return s.slice(bestStart, bestStart + bestLength);
}
