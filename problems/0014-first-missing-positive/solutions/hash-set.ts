export function firstMissingPositive(nums: number[]): number {
  const present = new Set(nums);
  // The answer is at most nums.length + 1, so this loop runs at most n + 1 times.
  let candidate = 1;
  while (present.has(candidate)) {
    candidate++;
  }
  return candidate;
}
