export function rob(nums: number[]): number {
  // memo[house] is the most cash obtainable from houses house..end, or -1 when unknown.
  const memo = new Array<number>(nums.length).fill(-1);
  const bestFrom = (house: number): number => {
    if (house >= nums.length) {
      return 0;
    }
    if (memo[house] === -1) {
      memo[house] = Math.max(bestFrom(house + 1), nums[house] + bestFrom(house + 2));
    }
    return memo[house];
  };
  return bestFrom(0);
}
