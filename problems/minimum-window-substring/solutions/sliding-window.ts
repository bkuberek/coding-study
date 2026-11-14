export function minWindow(s: string, t: string): string {
  const deficit = new Int32Array(128);
  for (let i = 0; i < t.length; i++) {
    deficit[t.charCodeAt(i)]++;
  }
  let missing = t.length;
  let bestStart = 0;
  let bestLength = 0;
  let left = 0;
  for (let right = 0; right < s.length; right++) {
    if (deficit[s.charCodeAt(right)]-- > 0) {
      missing--;
    }
    while (missing === 0) {
      if (bestLength === 0 || right - left + 1 < bestLength) {
        bestStart = left;
        bestLength = right - left + 1;
      }
      if (++deficit[s.charCodeAt(left)] > 0) {
        missing++;
      }
      left++;
    }
  }
  return s.slice(bestStart, bestStart + bestLength);
}
