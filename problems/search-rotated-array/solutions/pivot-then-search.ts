export function search(nums: number[], target: number): number {
  const pivot = indexOfMinimum(nums);
  const last = nums.length - 1;
  if (nums[pivot] <= target && target <= nums[last]) {
    return binarySearch(nums, target, pivot, last);
  }
  return binarySearch(nums, target, 0, pivot - 1);
}

function indexOfMinimum(nums: number[]): number {
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
  return low;
}

function binarySearch(nums: number[], target: number, from: number, to: number): number {
  let low = from;
  let high = to;
  while (low <= high) {
    const middle = (low + high) >>> 1;
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
