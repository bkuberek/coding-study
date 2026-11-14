export function findTargetSumWays(nums: number[], target: number): number {
  const total = nums.reduce((sum, value) => sum + value, 0);
  // ways[index][running + total] caches the count from that state; -1 is unknown.
  const ways = Array.from({ length: nums.length }, () =>
    new Array<number>(2 * total + 1).fill(-1),
  );
  const count = (index: number, running: number): number => {
    if (index === nums.length) {
      return running === target ? 1 : 0;
    }
    const offset = running + total;
    if (ways[index][offset] < 0) {
      ways[index][offset] =
        count(index + 1, running + nums[index]) + count(index + 1, running - nums[index]);
    }
    return ways[index][offset];
  };
  return count(0, 0);
}
