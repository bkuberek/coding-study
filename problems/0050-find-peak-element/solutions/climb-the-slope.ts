export function findPeakElement(nums: number[]): number {
  // Invariant: some peak of the whole array lies in [low, high].
  let low = 0;
  let high = nums.length - 1;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (nums[middle] < nums[middle + 1]) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }
  return low;
}
