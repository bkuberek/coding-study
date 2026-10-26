export function lengthOfLongestSubstring(s: string): number {
  let best = 0;
  for (let start = 0; start < s.length; start++) {
    const seen = new Set<string>();
    for (let end = start; end < s.length && !seen.has(s[end]); end++) {
      seen.add(s[end]);
    }
    best = Math.max(best, seen.size);
  }
  return best;
}
