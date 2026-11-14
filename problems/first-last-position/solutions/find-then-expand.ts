export function searchRange(nums: number[], target: number): number[] {
  let low = 0;
  let high = nums.length - 1;
  while (low <= high) {
    const middle = (low + high) >>> 1;
    if (nums[middle] === target) {
      let first = middle;
      let last = middle;
      while (first > 0 && nums[first - 1] === target) {
        first--;
      }
      while (last < nums.length - 1 && nums[last + 1] === target) {
        last++;
      }
      return [first, last];
    }
    if (nums[middle] < target) {
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  return [-1, -1];
}
