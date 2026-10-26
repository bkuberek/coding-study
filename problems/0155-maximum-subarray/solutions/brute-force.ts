export function maxSubArray(nums: number[]): number {
  let best = nums[0];
  for (let start = 0; start < nums.length; start++) {
    let total = 0;
    for (let end = start; end < nums.length; end++) {
      total += nums[end];
      best = Math.max(best, total);
    }
  }
  return best;
}
