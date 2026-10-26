export function lengthOfLIS(nums: number[]): number {
  // memo[start] is the longest increasing subsequence that begins at nums[start], or 0.
  const memo = new Array<number>(nums.length).fill(0);
  const longestFrom = (start: number): number => {
    if (memo[start] === 0) {
      let best = 1;
      for (let following = start + 1; following < nums.length; following++) {
        if (nums[following] > nums[start]) {
          best = Math.max(best, 1 + longestFrom(following));
        }
      }
      memo[start] = best;
    }
    return memo[start];
  };
  let answer = 0;
  for (let start = 0; start < nums.length; start++) {
    answer = Math.max(answer, longestFrom(start));
  }
  return answer;
}
