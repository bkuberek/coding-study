export function wordBreak(s: string, wordDict: string[]): boolean {
  const words = new Set(wordDict);
  const longest = Math.max(...wordDict.map((word) => word.length));
  // ok[i] is true when the prefix s[0..i) can be split into dictionary words.
  const ok = new Array<boolean>(s.length + 1).fill(false);
  ok[0] = true;
  for (let end = 1; end <= s.length; end++) {
    for (let start = Math.max(0, end - longest); start < end; start++) {
      if (ok[start] && words.has(s.slice(start, end))) {
        ok[end] = true;
        break;
      }
    }
  }
  return ok[s.length];
}
