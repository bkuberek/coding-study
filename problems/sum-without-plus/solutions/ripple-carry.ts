const WORD_BITS = 32;

export function getSum(a: number, b: number): number {
  // Bitwise operators work on 32-bit signed integers, matching the inputs exactly.
  let result = 0;
  let carry = 0;
  for (let position = 0; position < WORD_BITS; position++) {
    const x = (a >>> position) & 1;
    const y = (b >>> position) & 1;
    result |= (x ^ y ^ carry) << position;
    carry = (x & y) | (carry & (x ^ y)); // carry out: at least two of the three bits
  }
  return result; // `|` and `<<` already produce a signed 32-bit value
}
