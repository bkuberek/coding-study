export function climbStairs(n: number): number {
  // Before each iteration: twoBelow and oneBelow count the ways to reach the two steps
  // just below the one being computed.
  let twoBelow = 1;
  let oneBelow = 1;
  for (let step = 2; step <= n; step++) {
    [twoBelow, oneBelow] = [oneBelow, oneBelow + twoBelow];
  }
  return oneBelow;
}
