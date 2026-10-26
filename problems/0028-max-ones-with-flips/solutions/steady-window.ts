export function longestOnes(nums: number[], k: number): number {
  let left = 0;
  let flipsLeft = k;
  for (const value of nums) {
    if (value === 0) {
      flipsLeft--;
    }
    if (flipsLeft < 0) {
      if (nums[left++] === 0) {
        flipsLeft++;
      }
    }
  }
  return nums.length - left;
}
