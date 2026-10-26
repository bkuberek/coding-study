export function canPartition(nums: number[]): boolean {
  const total = nums.reduce((sum, value) => sum + value, 0);
  if (total % 2 === 1) {
    return false;
  }
  const target = total / 2;
  // reach[i][s] is true when some of the first i elements add up to exactly s.
  const reach = Array.from({ length: nums.length + 1 }, () =>
    new Array<boolean>(target + 1).fill(false),
  );
  reach[0][0] = true;
  for (let i = 1; i <= nums.length; i++) {
    const value = nums[i - 1];
    for (let s = 0; s <= target; s++) {
      reach[i][s] = reach[i - 1][s] || (s >= value && reach[i - 1][s - value]);
    }
  }
  return reach[nums.length][target];
}
