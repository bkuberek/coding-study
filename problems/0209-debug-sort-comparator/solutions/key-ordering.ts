function compareStrings(a: string, b: string): number {
  if (a < b) return -1;
  return a > b ? 1 : 0;
}

export function rankPlayers(names: string[], scores: number[]): string[] {
  const order = names.map((_, index) => index);
  order.sort((a, b) => {
    if (scores[a] !== scores[b]) {
      return scores[a] > scores[b] ? -1 : 1;
    }
    return compareStrings(names[a], names[b]);
  });
  return order.map((index) => names[index]);
}
