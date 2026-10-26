export function numDistinct(s: string, t: string): number {
  // ways[i][j] caches the occurrences of t[j:] as a subsequence of s[i:]; -1 is unknown.
  const ways = Array.from({ length: s.length }, () => new Array<number>(t.length).fill(-1));
  const count = (i: number, j: number): number => {
    if (j === t.length) {
      return 1; // the empty suffix of t occurs once
    }
    if (s.length - i < t.length - j) {
      return 0; // not enough characters left in s
    }
    if (ways[i][j] < 0) {
      // Either s[i] is skipped, or it is matched with t[j].
      ways[i][j] = count(i + 1, j) + (s[i] === t[j] ? count(i + 1, j + 1) : 0);
    }
    return ways[i][j];
  };
  return count(0, 0);
}
