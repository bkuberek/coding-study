export function lengthOfLongestSubstring(s: string): number {
  const lastSeen = new Int32Array(128).fill(-1);
  let left = 0;
  let best = 0;
  for (let right = 0; right < s.length; right++) {
    const code = s.charCodeAt(right);
    if (lastSeen[code] >= left) {
      left = lastSeen[code] + 1;
    }
    lastSeen[code] = right;
    best = Math.max(best, right - left + 1);
  }
  return best;
}
