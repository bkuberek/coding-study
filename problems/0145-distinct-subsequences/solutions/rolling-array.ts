export function numDistinct(s: string, t: string): number {
  // ways[j] counts the occurrences of t[:j] in the prefix of s read so far.
  const ways = new Array<number>(t.length + 1).fill(0);
  ways[0] = 1;
  for (const character of s) {
    // Right to left: ways[j - 1] still excludes this character, so it is used once.
    for (let j = t.length; j > 0; j--) {
      if (t[j - 1] === character) {
        ways[j] += ways[j - 1];
      }
    }
  }
  return ways[t.length];
}
