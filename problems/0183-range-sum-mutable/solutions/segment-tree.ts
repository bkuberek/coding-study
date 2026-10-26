export class NumArray {
  private readonly size: number;
  // Leaves at size .. 2 * size - 1; node i holds the sum of its children 2i and 2i + 1.
  private readonly tree: number[];

  constructor(nums: number[]) {
    this.size = nums.length;
    this.tree = new Array<number>(this.size).fill(0).concat(nums);
    for (let node = this.size - 1; node > 0; node--) {
      this.tree[node] = this.tree[2 * node] + this.tree[2 * node + 1];
    }
  }

  update(index: number, value: number): void {
    let node = index + this.size;
    this.tree[node] = value;
    while (node > 1) {
      node >>= 1;
      this.tree[node] = this.tree[2 * node] + this.tree[2 * node + 1];
    }
  }

  sumRange(left: number, right: number): number {
    let total = 0;
    // Half-open [low, high) over the leaves, narrowed one level per round.
    let low = left + this.size;
    let high = right + this.size + 1;
    while (low < high) {
      if (low & 1) {
        total += this.tree[low++];
      }
      if (high & 1) {
        total += this.tree[--high];
      }
      low >>= 1;
      high >>= 1;
    }
    return total;
  }
}
