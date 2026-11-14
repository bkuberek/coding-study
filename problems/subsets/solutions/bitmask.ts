export function subsets(nums: number[]): number[][] {
  const result: number[][] = [];
  // Bit i of mask says whether nums[i] belongs to the subset that mask encodes.
  for (let mask = 0; mask < 1 << nums.length; mask++) {
    result.push(nums.filter((_, i) => ((mask >> i) & 1) === 1));
  }
  return result;
}
