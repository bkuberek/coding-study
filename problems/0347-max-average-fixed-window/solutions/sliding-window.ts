export function maxWindowAverage(nums: number[], k: number): number {
  let windowSum = 0;
  for (let i = 0; i < k; i++) windowSum += nums[i];
  let best = windowSum;
  for (let right = k; right < nums.length; right++) {
    // Slide one step: the number at `right` enters and the one k places back leaves.
    windowSum += nums[right] - nums[right - k];
    best = Math.max(best, windowSum);
  }
  // Every window has k numbers, so the largest sum is the largest average. Divide once.
  return best / k;
}
