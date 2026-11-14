export function numDistinct(s: string, t: string): number {
  const rows = s.length;
  const columns = t.length;
  // ways[i][j] counts the occurrences of t[:j] in s[:i]; the empty t[:0] occurs once.
  const ways = Array.from({ length: rows + 1 }, () => new Array<number>(columns + 1).fill(0));
  for (let i = 0; i <= rows; i++) {
    ways[i][0] = 1;
  }
  for (let i = 1; i <= rows; i++) {
    for (let j = 1; j <= columns; j++) {
      // Occurrences that skip s[i - 1], plus those that match it with t[j - 1].
      ways[i][j] = ways[i - 1][j] + (s[i - 1] === t[j - 1] ? ways[i - 1][j - 1] : 0);
    }
  }
  return ways[rows][columns];
}
