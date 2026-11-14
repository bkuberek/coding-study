export function findTargetSumWays(nums: number[], target: number): number {
  const total = nums.reduce((sum, value) => sum + value, 0);
  if (Math.abs(target) > total) {
    return 0;
  }
  // ways[i][running + total] counts the sign assignments of nums[:i] with that running total.
  const ways = Array.from({ length: nums.length + 1 }, () => new Array<number>(2 * total + 1).fill(0));
  ways[0][total] = 1;
  for (let i = 0; i < nums.length; i++) {
    const value = nums[i];
    for (let offset = 0; offset <= 2 * total; offset++) {
      const count = ways[i][offset];
      if (count > 0) {
        ways[i + 1][offset + value] += count;
        ways[i + 1][offset - value] += count;
      }
    }
  }
  return ways[nums.length][target + total];
}
