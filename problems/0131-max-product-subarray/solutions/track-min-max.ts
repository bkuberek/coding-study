export function maxProduct(nums: number[]): number {
  // largest and smallest are the extreme products of subarrays that end at the current index.
  let largest = nums[0];
  let smallest = nums[0];
  let best = nums[0];
  for (let i = 1; i < nums.length; i++) {
    const value = nums[i];
    const extendLargest = largest * value;
    const extendSmallest = smallest * value;
    largest = Math.max(value, extendLargest, extendSmallest);
    smallest = Math.min(value, extendLargest, extendSmallest);
    best = Math.max(best, largest);
  }
  return best;
}
