export function missingNumber(nums: number[]): number {
  // A typed array sorts numerically (a plain array's default sort compares as strings).
  const sorted = Int32Array.from(nums).sort();
  // In the sorted array, value i sits at index i until the gap.
  for (let index = 0; index < sorted.length; index++) {
    if (sorted[index] !== index) {
      return index;
    }
  }
  return nums.length;
}
