// Debug: Leaderboard Comparator. Some tests fail: find the bug and fix it.
const SCORE_EPSILON = 1;

export function rankPlayers(names: string[], scores: number[]): string[] {
  const order = names.map((_, index) => index);
  order.sort((a, b) => {
    if (Math.abs(scores[a] - scores[b]) <= SCORE_EPSILON) {
      return names[a] < names[b] ? -1 : 1;
    }
    return scores[b] - scores[a];
  });
  return order.map((index) => names[index]);
}
