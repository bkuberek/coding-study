export function climbStairs(n: number): number {
  // memo[step] is 0 until the count for `step` has been computed.
  const memo = new Array<number>(n + 1).fill(0);
  const ways = (step: number): number => {
    if (step <= 1) {
      return 1;
    }
    if (memo[step] === 0) {
      memo[step] = ways(step - 1) + ways(step - 2);
    }
    return memo[step];
  };
  return ways(n);
}
