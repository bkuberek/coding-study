export class MedianFinder {
  private readonly values: number[] = []; // every number so far, ascending

  addNum(num: number): void {
    // Binary search for the first value >= num, then open a slot there.
    let low = 0;
    let high = this.values.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (this.values[middle] < num) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    this.values.splice(low, 0, num);
  }

  findMedian(): number {
    const values = this.values;
    const middle = values.length >> 1;
    return values.length % 2 === 1 ? values[middle] : (values[middle - 1] + values[middle]) / 2;
  }
}
