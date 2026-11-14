export function maxSlidingWindow(nums: number[], k: number): number[] {
  const maxima: number[] = [];
  for (let start = 0; start + k <= nums.length; start++) {
    let best = nums[start];
    for (let i = start + 1; i < start + k; i++) {
      best = Math.max(best, nums[i]);
    }
    maxima.push(best);
  }
  return maxima;
}
