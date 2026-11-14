export function majorityElement(nums: number[]): number {
  let candidate = nums[0];
  let votes = 0;
  for (const value of nums) {
    if (votes === 0) {
      candidate = value;
    }
    votes += value === candidate ? 1 : -1;
  }
  return candidate;
}
