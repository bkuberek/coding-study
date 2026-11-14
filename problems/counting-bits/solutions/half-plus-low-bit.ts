export function countBits(n: number): number[] {
  const bits = new Array<number>(n + 1).fill(0);
  for (let i = 1; i <= n; i++) {
    // i >> 1 drops the lowest bit of i and is smaller than i, so its count is known.
    bits[i] = bits[i >> 1] + (i & 1);
  }
  return bits;
}
