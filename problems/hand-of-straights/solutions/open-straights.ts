export function isNStraightHand(hand: number[], groupSize: number): boolean {
  if (hand.length % groupSize !== 0) {
    return false;
  }
  const counts = new Map<number, number>();
  for (const card of hand) {
    counts.set(card, (counts.get(card) ?? 0) + 1);
  }
  const values = [...counts.keys()].sort((a, b) => a - b);
  let openCount = 0; // straights started but not yet complete; each needs the current value
  // opened[i] is how many straights started at the i-th distinct value (a queue of the last
  // groupSize entries, read from `head`).
  const opened: number[] = [];
  let head = 0;
  let previous = -1;
  for (const value of values) {
    if (openCount > 0 && value !== previous + 1) {
      return false; // an open straight needs previous + 1, which is missing
    }
    const count = counts.get(value)!;
    if (count < openCount) {
      return false;
    }
    const fresh = count - openCount;
    opened.push(fresh);
    openCount += fresh;
    if (opened.length - head === groupSize) {
      // The straights opened groupSize values ago end with this value.
      openCount -= opened[head++];
    }
    previous = value;
  }
  return openCount === 0;
}
