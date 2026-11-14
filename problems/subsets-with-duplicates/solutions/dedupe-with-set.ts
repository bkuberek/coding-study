export function subsetsWithDup(nums: number[]): number[][] {
  const ordered = [...nums].sort((a, b) => a - b);
  // Taking values in sorted order gives every multiset one canonical key to dedupe on.
  const distinct = new Map<string, number[]>();
  for (let mask = 0; mask < 1 << ordered.length; mask++) {
    const subset = ordered.filter((_, i) => ((mask >> i) & 1) === 1);
    distinct.set(subset.join(","), subset);
  }
  return [...distinct.values()];
}
