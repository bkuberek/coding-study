export class KthLargestTracker {
  private readonly k: number;
  private readonly values: number[]; // every number so far, ascending

  constructor(k: number, nums: number[]) {
    this.k = k;
    this.values = [...nums].sort((a, b) => a - b);
  }

  add(value: number): number {
    // Binary search for the first entry >= value, then open a slot there. splice is O(n).
    let low = 0;
    let high = this.values.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (this.values[middle] < value) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    this.values.splice(low, 0, value);
    // The kth largest is the kth entry from the end.
    return this.values[this.values.length - this.k];
  }
}
