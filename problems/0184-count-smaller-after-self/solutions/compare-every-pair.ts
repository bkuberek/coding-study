export function countSmaller(nums: number[]): number[] {
  const counts = new Array<number>(nums.length).fill(0);
  for (let i = 0; i < nums.length; i++) {
    for (let j = i + 1; j < nums.length; j++) {
      if (nums[j] < nums[i]) {
        counts[i]++;
      }
    }
  }
  return counts;
}
