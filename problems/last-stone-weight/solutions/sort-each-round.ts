export function lastStoneWeight(stones: number[]): number {
  const remaining = [...stones];
  while (remaining.length > 1) {
    remaining.sort((a, b) => a - b);
    const heaviest = remaining.pop()!;
    const second = remaining.pop()!;
    if (heaviest !== second) {
      remaining.push(heaviest - second);
    }
  }
  return remaining.length === 1 ? remaining[0] : 0;
}
