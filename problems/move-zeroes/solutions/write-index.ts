export function moveZeroes(nums: number[]): void {
  let write = 0;
  for (const value of nums) {
    if (value !== 0) {
      nums[write++] = value;
    }
  }
  nums.fill(0, write);
}
