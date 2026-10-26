export function canPartition(nums: number[]): boolean {
  const total = nums.reduce((sum, value) => sum + value, 0);
  if (total % 2 === 1) {
    return false;
  }
  const target = total / 2;
  // reachable[s] is true when some of the elements seen so far add up to exactly s.
  const reachable = new Array<boolean>(target + 1).fill(false);
  reachable[0] = true;
  for (const value of nums) {
    // Right to left, so reachable[s - value] still describes the elements before `value`.
    for (let s = target; s >= value; s--) {
      if (reachable[s - value]) {
        reachable[s] = true;
      }
    }
    if (reachable[target]) {
      return true;
    }
  }
  return reachable[target];
}
