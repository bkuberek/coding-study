export function subarraySum(nums: number[], k: number): number {
  let count = 0;
  for (let start = 0; start < nums.length; start++) {
    let total = 0;
    for (let end = start; end < nums.length; end++) {
      total += nums[end];
      if (total === k) {
        count++;
      }
    }
  }
  return count;
}
