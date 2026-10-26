export function canJump(nums: number[]): boolean {
  const last = nums.length - 1;
  // reachable[i] is true once some sequence of jumps from index 0 is known to land on i.
  const reachable = new Array<boolean>(nums.length).fill(false);
  reachable[0] = true;
  for (let i = 0; i < nums.length; i++) {
    if (!reachable[i]) {
      continue;
    }
    if (i === last) {
      return true;
    }
    const farthest = Math.min(last, i + nums[i]);
    for (let target = i + 1; target <= farthest; target++) {
      reachable[target] = true;
    }
  }
  return reachable[last];
}
