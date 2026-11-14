export function productExceptSelf(nums: number[]): number[] {
  const n = nums.length;
  const left = new Array<number>(n).fill(1); // left[i] is the product of nums[0..i-1]
  for (let i = 1; i < n; i++) {
    left[i] = left[i - 1] * nums[i - 1];
  }
  const right = new Array<number>(n).fill(1); // right[i] is the product of nums[i+1..n-1]
  for (let i = n - 2; i >= 0; i--) {
    right[i] = right[i + 1] * nums[i + 1];
  }
  return left.map((before, i) => before * right[i]);
}
