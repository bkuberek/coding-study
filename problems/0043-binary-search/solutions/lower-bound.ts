export function search(nums: number[], target: number): number {
  // Find the first index whose value is >= target, in the half-open range [low, high).
  let low = 0;
  let high = nums.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (nums[middle] < target) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }
  return low < nums.length && nums[low] === target ? low : -1;
}
