function swap(nums: number[], i: number, j: number): void {
  const value = nums[i];
  nums[i] = nums[j];
  nums[j] = value;
}

export function sortColors(nums: number[]): void {
  let low = 0;
  let mid = 0;
  let high = nums.length - 1;
  while (mid <= high) {
    if (nums[mid] === 0) {
      swap(nums, low++, mid++);
    } else if (nums[mid] === 1) {
      mid++;
    } else {
      swap(nums, mid, high--);
    }
  }
}
