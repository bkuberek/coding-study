export function isNStraightHand(hand: number[], groupSize: number): boolean {
  if (hand.length % groupSize !== 0) {
    return false;
  }
  const counts = new Map<number, number>();
  for (const card of hand) {
    counts.set(card, (counts.get(card) ?? 0) + 1);
  }
  const values = [...counts.keys()].sort((a, b) => a - b);
  for (const value of values) {
    const starting = counts.get(value)!;
    if (starting === 0) {
      continue;
    }
    // Every card left at the smallest remaining value starts its own straight.
    for (let following = value; following < value + groupSize; following++) {
      const available = counts.get(following) ?? 0;
      if (available < starting) {
        return false;
      }
      counts.set(following, available - starting);
    }
  }
  return true;
}
