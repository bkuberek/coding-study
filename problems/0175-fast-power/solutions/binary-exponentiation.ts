export function myPow(x: number, n: number): number {
  let base = x;
  // Numbers are doubles, so -(-2^31) is exact; avoid the 32-bit bitwise operators on it.
  let exponent = n;
  if (exponent < 0) {
    base = 1 / base;
    exponent = -exponent;
  }
  let result = 1;
  // Invariant: result * base^exponent equals the original x^n.
  while (exponent > 0) {
    if (exponent % 2 === 1) {
      result *= base;
    }
    base *= base;
    exponent = Math.floor(exponent / 2);
  }
  return result;
}
