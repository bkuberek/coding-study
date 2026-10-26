export function longestOnes(nums: number[], k: number): number {
  let best = 0;
  for (let start = 0; start < nums.length; start++) {
    let zeros = 0;
    let end = start;
    while (end < nums.length) {
      if (nums[end] === 0) {
        if (zeros === k) {
          break;
        }
        zeros++;
      }
      end++;
    }
    best = Math.max(best, end - start);
  }
  return best;
}
