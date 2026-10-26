export function hammingWeight(n: number): number {
  // Bitwise operators work on 32-bit signed integers: `n | 0` keeps the same 32 bits
  // (values from 2^31 up become negative), and the loop below only cares about the bits.
  let word = n | 0;
  let count = 0;
  while (word !== 0) {
    word &= word - 1; // clears the lowest set bit
    count++;
  }
  return count;
}
