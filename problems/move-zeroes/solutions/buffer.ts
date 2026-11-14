export function moveZeroes(nums: number[]): void {
  const nonZero = nums.filter((value) => value !== 0);
  for (let i = 0; i < nums.length; i++) {
    nums[i] = i < nonZero.length ? nonZero[i] : 0;
  }
}
