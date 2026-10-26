export function findMin(nums: number[]): number {
  let smallest = nums[0];
  for (const value of nums) {
    if (value < smallest) {
      smallest = value;
    }
  }
  return smallest;
}
