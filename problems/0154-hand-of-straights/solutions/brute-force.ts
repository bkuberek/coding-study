export function isNStraightHand(hand: number[], groupSize: number): boolean {
  if (hand.length % groupSize !== 0) {
    return false;
  }
  const cards = [...hand].sort((a, b) => a - b);
  while (cards.length > 0) {
    // The smallest card must start a straight; remove that straight card by card.
    const smallest = cards.shift()!;
    for (let value = smallest + 1; value < smallest + groupSize; value++) {
      const position = cards.indexOf(value);
      if (position === -1) {
        return false;
      }
      cards.splice(position, 1);
    }
  }
  return true;
}
