export function combinationSum2(candidates: number[], target: number): number[][] {
  const ordered = [...candidates].sort((a, b) => a - b);
  // Values taken in sorted order give each multiset one canonical key.
  const found = new Map<string, number[]>();
  for (let mask = 0; mask < 1 << ordered.length; mask++) {
    const chosen = ordered.filter((_, i) => ((mask >> i) & 1) === 1);
    if (chosen.reduce((total, value) => total + value, 0) === target) {
      found.set(chosen.join(","), chosen);
    }
  }
  return [...found.values()];
}
