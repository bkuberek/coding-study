export function productExceptSelf(nums: number[]): number[] {
  const n = nums.length;
  const answer = new Array<number>(n).fill(1);
  for (let i = 1; i < n; i++) {
    answer[i] = answer[i - 1] * nums[i - 1]; // product of nums[0..i-1]
  }
  let after = 1; // product of nums[i+1..n-1]
  for (let i = n - 1; i >= 0; i--) {
    answer[i] *= after;
    after *= nums[i];
  }
  return answer;
}
