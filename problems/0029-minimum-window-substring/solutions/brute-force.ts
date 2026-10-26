export function minWindow(s: string, t: string): string {
  const need = new Int32Array(128);
  for (let i = 0; i < t.length; i++) {
    need[t.charCodeAt(i)]++;
  }
  let bestStart = 0;
  let bestLength = 0;
  for (let start = 0; start < s.length; start++) {
    const remaining = need.slice();
    let missing = t.length;
    for (let end = start; end < s.length; end++) {
      if (remaining[s.charCodeAt(end)]-- > 0) {
        missing--;
      }
      if (missing === 0) {
        if (bestLength === 0 || end - start + 1 < bestLength) {
          bestStart = start;
          bestLength = end - start + 1;
        }
        break;
      }
    }
  }
  return s.slice(bestStart, bestStart + bestLength);
}
