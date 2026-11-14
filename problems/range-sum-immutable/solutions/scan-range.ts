export class NumArray {
  private readonly nums: number[];

  constructor(nums: number[]) {
    this.nums = nums;
  }

  sumRange(left: number, right: number): number {
    let total = 0;
    for (let i = left; i <= right; i++) {
      total += this.nums[i];
    }
    return total;
  }
}
