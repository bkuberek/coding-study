export function minDistance(word1: string, word2: string): number {
  // cost[i][j] caches the distance between the suffixes word1[i:] and word2[j:]; -1 is unknown.
  const cost = Array.from({ length: word1.length + 1 }, () =>
    new Int16Array(word2.length + 1).fill(-1),
  );
  const solve = (i: number, j: number): number => {
    if (i === word1.length) {
      return word2.length - j; // insert the rest of word2
    }
    if (j === word2.length) {
      return word1.length - i; // delete the rest of word1
    }
    if (cost[i][j] < 0) {
      cost[i][j] =
        word1[i] === word2[j]
          ? solve(i + 1, j + 1)
          : 1 + Math.min(solve(i + 1, j), solve(i, j + 1), solve(i + 1, j + 1));
    }
    return cost[i][j];
  };
  return solve(0, 0);
}
