export function maxSubArray(nums: number[]): number {
  // endingHere is the best sum of a subarray that ends at the current index.
  let endingHere = nums[0];
  let best = nums[0];
  for (let index = 1; index < nums.length; index++) {
    endingHere = Math.max(nums[index], endingHere + nums[index]);
    best = Math.max(best, endingHere);
  }
  return best;
}
