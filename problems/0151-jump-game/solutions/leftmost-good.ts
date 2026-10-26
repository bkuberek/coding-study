export function canJump(nums: number[]): boolean {
  let goal = nums.length - 1; // the leftmost index known to reach the last index
  for (let i = nums.length - 2; i >= 0; i--) {
    if (i + nums[i] >= goal) {
      goal = i;
    }
  }
  return goal === 0;
}
