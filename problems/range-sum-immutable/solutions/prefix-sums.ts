export class NumArray {
  // prefix[i] is the sum of nums[0..i-1]. Sums stay below 2^53, so a number holds them exactly.
  private readonly prefix: number[];

  constructor(nums: number[]) {
    this.prefix = new Array<number>(nums.length + 1);
    this.prefix[0] = 0;
    for (let i = 0; i < nums.length; i++) {
      this.prefix[i + 1] = this.prefix[i] + nums[i];
    }
  }

  sumRange(left: number, right: number): number {
    return this.prefix[right + 1] - this.prefix[left];
  }
}
