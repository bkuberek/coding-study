export function findMissingAndDuplicates(nums: number[]): number[][] {
  const seen = new Set<number>();
  const repeated = new Set<number>();
  for (const value of nums) {
    if (seen.has(value)) {
      repeated.add(value);
    }
    seen.add(value);
  }
  // Walking 1..n instead of the sets keeps both answers sorted without a sort.
  const missing: number[] = [];
  const duplicated: number[] = [];
  for (let value = 1; value <= nums.length; value++) {
    if (!seen.has(value)) {
      missing.push(value);
    }
    if (repeated.has(value)) {
      duplicated.push(value);
    }
  }
  return [missing, duplicated];
}
