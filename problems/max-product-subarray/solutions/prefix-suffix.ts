export function maxProduct(nums: number[]): number {
  // Within a zero-free run, the best product is a prefix or a suffix of the run, so the
  // running products from both ends (restarted after each zero) cover every candidate.
  let best = Math.max(...nums);
  let fromLeft = 1;
  let fromRight = 1;
  const n = nums.length;
  for (let i = 0; i < n; i++) {
    fromLeft = (fromLeft === 0 ? 1 : fromLeft) * nums[i];
    fromRight = (fromRight === 0 ? 1 : fromRight) * nums[n - 1 - i];
    best = Math.max(best, fromLeft, fromRight);
  }
  return best;
}
