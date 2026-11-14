export function searchInsert(nums: number[], target: number): number {
  // In a sorted array, target belongs right after every smaller value.
  let smaller = 0;
  for (const value of nums) {
    if (value < target) {
      smaller++;
    }
  }
  return smaller;
}
