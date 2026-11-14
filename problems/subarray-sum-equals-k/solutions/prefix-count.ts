export function subarraySum(nums: number[], k: number): number {
  // seen maps a prefix sum to how many prefixes so far have it; the empty prefix sums to 0.
  const seen = new Map<number, number>([[0, 1]]);
  let total = 0;
  let count = 0;
  for (const value of nums) {
    total += value;
    count += seen.get(total - k) ?? 0;
    seen.set(total, (seen.get(total) ?? 0) + 1);
  }
  return count;
}
