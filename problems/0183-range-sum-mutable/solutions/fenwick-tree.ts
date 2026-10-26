export class NumArray {
  private readonly values: number[];
  // tree[i] (1-based) holds the sum of the i & -i values ending at position i - 1.
  // Sums stay below 2^53, so plain numbers hold them exactly.
  private readonly tree: number[];

  constructor(nums: number[]) {
    this.values = [...nums];
    this.tree = [0, ...nums];
    for (let i = 1; i <= nums.length; i++) {
      const parent = i + (i & -i);
      if (parent <= nums.length) {
        this.tree[parent] += this.tree[i];
      }
    }
  }

  update(index: number, value: number): void {
    const delta = value - this.values[index];
    this.values[index] = value;
    for (let i = index + 1; i < this.tree.length; i += i & -i) {
      this.tree[i] += delta;
    }
  }

  sumRange(left: number, right: number): number {
    return this.prefix(right + 1) - this.prefix(left);
  }

  /** Sum of the first count values. */
  private prefix(count: number): number {
    let total = 0;
    for (let i = count; i > 0; i -= i & -i) {
      total += this.tree[i];
    }
    return total;
  }
}
