export function firstMissingPositive(nums: number[]): number {
  let candidate = 1;
  // includes() is a linear scan: O(n) per candidate.
  while (nums.includes(candidate)) {
    candidate++;
  }
  return candidate;
}
