export function findTargetSumWays(nums: number[], target: number): number {
  const count = (index: number, total: number): number => {
    if (index === nums.length) {
      return total === target ? 1 : 0;
    }
    // Give nums[index] a plus sign, then a minus sign.
    return count(index + 1, total + nums[index]) + count(index + 1, total - nums[index]);
  };
  return count(0, 0);
}
