export function singleNumber(nums: number[]): number {
  // ^ converts its operands to 32-bit signed integers, which every input already is,
  // so the result is exact (and signed) here.
  let result = 0;
  for (const value of nums) {
    result ^= value;
  }
  return result;
}
