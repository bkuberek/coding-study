const MODULUS = 1_000_000_007;

export function createSortedArray(instructions: number[]): number {
  const largest = instructions.reduce((a, b) => Math.max(a, b));
  // tree[i] (1-based) counts the inserted values in (i - (i & -i), i].
  const tree = new Int32Array(largest + 1);

  const countAtMost = (value: number): number => {
    let total = 0;
    for (let i = value; i > 0; i -= i & -i) {
      total += tree[i];
    }
    return total;
  };

  let cost = 0;
  instructions.forEach((value, inserted) => {
    const less = countAtMost(value - 1);
    const greater = inserted - countAtMost(value);
    cost = (cost + Math.min(less, greater)) % MODULUS;
    for (let i = value; i <= largest; i += i & -i) {
      tree[i]++;
    }
  });
  return cost;
}
