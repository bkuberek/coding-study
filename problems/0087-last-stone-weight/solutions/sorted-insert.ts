export function lastStoneWeight(stones: number[]): number {
  const remaining = [...stones].sort((a, b) => a - b);
  while (remaining.length > 1) {
    const heaviest = remaining.pop()!;
    const second = remaining.pop()!;
    if (heaviest !== second) {
      const stone = heaviest - second;
      // Binary search finds the slot in O(log n); splice shifts the tail to open it in O(n).
      remaining.splice(lowerBound(remaining, stone), 0, stone);
    }
  }
  return remaining.length === 1 ? remaining[0] : 0;
}

function lowerBound(sorted: number[], value: number): number {
  let low = 0;
  let high = sorted.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (sorted[middle] < value) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }
  return low;
}
