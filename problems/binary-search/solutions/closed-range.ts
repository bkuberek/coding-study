export function search(nums: number[], target: number): number {
  // Invariant: if target is in nums, its index lies in [low, high].
  let low = 0;
  let high = nums.length - 1;
  while (low <= high) {
    const middle = low + ((high - low) >> 1);
    if (nums[middle] === target) {
      return middle;
    }
    if (nums[middle] < target) {
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  return -1;
}
