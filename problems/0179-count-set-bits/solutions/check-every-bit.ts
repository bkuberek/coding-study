const WORD_BITS = 32;

export function hammingWeight(n: number): number {
  // n can reach 2^32 - 1. `n >>> position` first converts n to an unsigned 32-bit integer,
  // which keeps all 32 bits (a signed `>>` would treat the top bit as a sign).
  let count = 0;
  for (let position = 0; position < WORD_BITS; position++) {
    count += (n >>> position) & 1;
  }
  return count;
}
