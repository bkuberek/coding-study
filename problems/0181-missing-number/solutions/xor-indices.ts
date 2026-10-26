export function missingNumber(nums: number[]): number {
  // Start with n, then fold in every index and value; present numbers cancel in pairs.
  let result = nums.length;
  for (let index = 0; index < nums.length; index++) {
    result ^= index ^ nums[index];
  }
  return result;
}
