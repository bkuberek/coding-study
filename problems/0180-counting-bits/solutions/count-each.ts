export function countBits(n: number): number[] {
  const bits = new Array<number>(n + 1);
  for (let i = 0; i <= n; i++) {
    let count = 0;
    for (let word = i; word !== 0; word &= word - 1) {
      count++; // each step clears the lowest set bit
    }
    bits[i] = count;
  }
  return bits;
}
