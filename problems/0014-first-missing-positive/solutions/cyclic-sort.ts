export function firstMissingPositive(nums: number[]): number {
  const n = nums.length;
  for (let i = 0; i < n; i++) {
    // Swap nums[i] to its home index nums[i] - 1 until the value here has no home in
    // range or its home already holds it. Every swap settles one value for good.
    while (nums[i] >= 1 && nums[i] <= n && nums[nums[i] - 1] !== nums[i]) {
      const home = nums[i] - 1;
      [nums[i], nums[home]] = [nums[home], nums[i]];
    }
  }
  for (let i = 0; i < n; i++) {
    if (nums[i] !== i + 1) {
      return i + 1;
    }
  }
  return n + 1;
}
