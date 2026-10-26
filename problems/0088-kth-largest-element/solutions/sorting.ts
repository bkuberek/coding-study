export function findKthLargest(nums: number[], k: number): number {
  // A typed-array copy sorts numerically without a comparator.
  const sorted = Int32Array.from(nums).sort();
  return sorted[sorted.length - k];
}
