export function runningMax(nums: number[]): number[] {
  const result: number[] = [];
  let best = nums[0];
  for (const value of nums) {
    best = Math.max(best, value);
    result.push(best);
  }
  return result;
}
