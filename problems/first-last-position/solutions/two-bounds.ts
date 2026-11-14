export function searchRange(nums: number[], target: number): number[] {
  const first = firstIndex(nums, (value) => value >= target);
  if (first === nums.length || nums[first] !== target) {
    return [-1, -1];
  }
  return [first, firstIndex(nums, (value) => value > target) - 1];
}

// The smallest index whose value satisfies the monotone predicate, or nums.length.
function firstIndex(nums: number[], isPast: (value: number) => boolean): number {
  let low = 0;
  let high = nums.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (isPast(nums[middle])) {
      high = middle;
    } else {
      low = middle + 1;
    }
  }
  return low;
}
