export function maxProduct(nums: number[]): number {
  let best = nums[0];
  for (let start = 0; start < nums.length; start++) {
    let product = 1;
    for (let end = start; end < nums.length; end++) {
      product *= nums[end];
      best = Math.max(best, product);
    }
  }
  return best;
}
