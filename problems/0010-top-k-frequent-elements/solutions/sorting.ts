export function topKFrequent(nums: number[], k: number): number[] {
  const counts = new Map<number, number>();
  for (const value of nums) {
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, k)
    .map(([value]) => value);
}
