export function findTargetSumWays(nums: number[], target: number): number {
  const total = nums.reduce((sum, value) => sum + value, 0);
  // With P the plus part: P - (total - P) = target, so P = (total + target) / 2.
  if (Math.abs(target) > total || (total + target) % 2 !== 0) {
    return 0;
  }
  const plus = (total + target) / 2;
  // ways[p] counts the subsets of the values seen so far that add up to p.
  const ways = new Array<number>(plus + 1).fill(0);
  ways[0] = 1;
  for (const value of nums) {
    // Decreasing p: ways[p - value] still excludes this value, so it is used at most once.
    for (let p = plus; p >= value; p--) {
      ways[p] += ways[p - value];
    }
  }
  return ways[plus];
}
