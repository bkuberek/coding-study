// Running Maximum (debugging): some tests fail. Find the bug and fix it.
export function runningMax(nums: number[]): number[] {
  const result: number[] = [];
  let best = 0;
  for (const value of nums) {
    best = Math.max(best, value);
    result.push(best);
  }
  return result;
}
