export function findMin(nums: number[]): number {
  // Invariant: the index of the minimum lies in [low, high].
  let low = 0;
  let high = nums.length - 1;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (nums[middle] > nums[high]) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }
  return nums[low];
}
