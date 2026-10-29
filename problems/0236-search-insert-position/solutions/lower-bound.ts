export function searchInsert(nums: number[], target: number): number {
  let low = 0;
  let high = nums.length; // the answer lies in [low, high]
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (nums[middle] < target) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }
  return low;
}
