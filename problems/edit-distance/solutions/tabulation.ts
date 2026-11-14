export function minDistance(word1: string, word2: string): number {
  const rows = word1.length;
  const columns = word2.length;
  // cost[i][j] is the distance between the prefixes word1[:i] and word2[:j]. Turning a prefix
  // into the empty word takes one deletion per character, and the reverse one insertion.
  const cost = Array.from({ length: rows + 1 }, () => new Int32Array(columns + 1));
  for (let i = 0; i <= rows; i++) {
    cost[i][0] = i;
  }
  for (let j = 0; j <= columns; j++) {
    cost[0][j] = j;
  }
  for (let i = 1; i <= rows; i++) {
    for (let j = 1; j <= columns; j++) {
      cost[i][j] =
        word1[i - 1] === word2[j - 1]
          ? cost[i - 1][j - 1]
          : 1 + Math.min(cost[i - 1][j], cost[i][j - 1], cost[i - 1][j - 1]);
    }
  }
  return cost[rows][columns];
}
