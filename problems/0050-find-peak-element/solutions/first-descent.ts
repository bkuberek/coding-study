export function findPeakElement(nums: number[]): number {
  // Before the first descent the values only rise, so the element just before it beats both
  // neighbors. With no descent at all, the last element is the peak.
  for (let i = 0; i < nums.length - 1; i++) {
    if (nums[i] > nums[i + 1]) {
      return i;
    }
  }
  return nums.length - 1;
}
