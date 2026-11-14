export function minSubArrayLen(target: number, nums: number[]): number {
  let best = 0;
  let total = 0;
  let left = 0;
  for (let right = 0; right < nums.length; right++) {
    total += nums[right];
    while (total >= target) {
      if (best === 0 || right - left + 1 < best) {
        best = right - left + 1;
      }
      total -= nums[left++];
    }
  }
  return best;
}
