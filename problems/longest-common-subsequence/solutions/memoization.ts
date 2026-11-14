export function longestCommonSubsequence(text1: string, text2: string): number {
  // best[i][j] caches the answer for the suffixes text1[i:] and text2[j:]; -1 is unknown.
  const best = Array.from({ length: text1.length }, () => new Int16Array(text2.length).fill(-1));
  const solve = (i: number, j: number): number => {
    if (i === text1.length || j === text2.length) {
      return 0;
    }
    if (best[i][j] < 0) {
      best[i][j] =
        text1[i] === text2[j] ? 1 + solve(i + 1, j + 1) : Math.max(solve(i + 1, j), solve(i, j + 1));
    }
    return best[i][j];
  };
  return solve(0, 0);
}
