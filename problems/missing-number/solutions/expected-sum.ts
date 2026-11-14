export function missingNumber(nums: number[]): number {
  const n = nums.length;
  // At most 5 * 10^9, exact in a double.
  let difference = (n * (n + 1)) / 2;
  for (const value of nums) {
    difference -= value;
  }
  return difference;
}
