export function checkSubarraySum(nums: number[], k: number): boolean {
  for (let start = 0; start < nums.length; start++) {
    // Sums reach 10^14, still exact in a double (below 2^53).
    let total = nums[start];
    for (let end = start + 1; end < nums.length; end++) {
      total += nums[end];
      if (total % k === 0) {
        return true;
      }
    }
  }
  return false;
}
