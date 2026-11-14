export function longestCommonSubsequence(text1: string, text2: string): number {
  const rows = text1.length;
  const columns = text2.length;
  // best[i][j] is the answer for the prefixes text1[:i] and text2[:j]; row and column 0
  // stand for an empty prefix.
  const best = Array.from({ length: rows + 1 }, () => new Int32Array(columns + 1));
  for (let i = 1; i <= rows; i++) {
    for (let j = 1; j <= columns; j++) {
      best[i][j] =
        text1[i - 1] === text2[j - 1]
          ? best[i - 1][j - 1] + 1
          : Math.max(best[i - 1][j], best[i][j - 1]);
    }
  }
  return best[rows][columns];
}
