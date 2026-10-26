export function minSubArrayLen(target: number, nums: number[]): number {
  let best = 0;
  for (let start = 0; start < nums.length; start++) {
    let total = 0;
    for (let end = start; end < nums.length; end++) {
      total += nums[end];
      if (total >= target) {
        if (best === 0 || end - start + 1 < best) {
          best = end - start + 1;
        }
        break;
      }
    }
  }
  return best;
}
