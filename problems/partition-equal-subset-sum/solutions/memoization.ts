const UNKNOWN = 0;
const YES = 1;
const NO = 2;

export function canPartition(nums: number[]): boolean {
  const total = nums.reduce((sum, value) => sum + value, 0);
  if (total % 2 === 1) {
    return false;
  }
  const target = total / 2;
  // memo[index][remaining] answers "can nums[index..] add up to exactly remaining?".
  const memo = Array.from({ length: nums.length }, () => new Uint8Array(target + 1));
  const reachable = (index: number, remaining: number): boolean => {
    if (remaining === 0) {
      return true;
    }
    if (index === nums.length || remaining < 0) {
      return false;
    }
    if (memo[index][remaining] === UNKNOWN) {
      const found =
        reachable(index + 1, remaining - nums[index]) || reachable(index + 1, remaining);
      memo[index][remaining] = found ? YES : NO;
    }
    return memo[index][remaining] === YES;
  };
  return reachable(0, target);
}
