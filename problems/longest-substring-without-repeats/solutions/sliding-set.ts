export function lengthOfLongestSubstring(s: string): number {
  const window = new Set<string>();
  let left = 0;
  let best = 0;
  for (const ch of s) {
    while (window.has(ch)) {
      window.delete(s[left]);
      left++;
    }
    window.add(ch);
    best = Math.max(best, window.size);
  }
  return best;
}
