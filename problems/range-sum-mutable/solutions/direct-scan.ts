export class NumArray {
  private readonly nums: number[];

  constructor(nums: number[]) {
    this.nums = [...nums];
  }

  update(index: number, value: number): void {
    this.nums[index] = value;
  }

  sumRange(left: number, right: number): number {
    let total = 0;
    for (let i = left; i <= right; i++) {
      total += this.nums[i];
    }
    return total;
  }
}
