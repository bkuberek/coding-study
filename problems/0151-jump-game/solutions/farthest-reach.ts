export function canJump(nums: number[]): boolean {
  let farthest = 0; // every index up to `farthest` is reachable
  for (let i = 0; i < nums.length; i++) {
    if (i > farthest) {
      return false;
    }
    farthest = Math.max(farthest, i + nums[i]);
  }
  return true;
}
