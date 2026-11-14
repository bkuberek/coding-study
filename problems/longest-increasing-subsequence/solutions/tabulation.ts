export function lengthOfLIS(nums: number[]): number {
  // ending[i] is the length of the longest increasing subsequence that ends at index i.
  const ending = new Array<number>(nums.length).fill(1);
  for (let i = 1; i < nums.length; i++) {
    for (let j = 0; j < i; j++) {
      if (nums[j] < nums[i] && ending[j] + 1 > ending[i]) {
        ending[i] = ending[j] + 1;
      }
    }
  }
  return Math.max(...ending);
}
