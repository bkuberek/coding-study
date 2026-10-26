export function rob(nums: number[]): number {
  // best[i] is the most cash obtainable from the first i houses.
  const best = new Array<number>(nums.length + 1).fill(0);
  best[1] = nums[0];
  for (let i = 2; i <= nums.length; i++) {
    best[i] = Math.max(best[i - 1], best[i - 2] + nums[i - 1]);
  }
  return best[nums.length];
}
