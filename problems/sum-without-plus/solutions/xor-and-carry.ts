export function getSum(a: number, b: number): number {
  // `&`, `^` and `<<` work on 32-bit signed integers, so the carry falls off the top bit
  // exactly as in hardware and the loop ends after at most 32 rounds.
  while (b !== 0) {
    const carry = (a & b) << 1;
    a ^= b; // the sum of every column, ignoring carries
    b = carry;
  }
  return a;
}
