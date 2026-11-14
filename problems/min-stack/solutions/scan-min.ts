export class MinStack {
  private readonly values: number[] = [];

  push(value: number): void {
    this.values.push(value);
  }

  pop(): void {
    this.values.pop();
  }

  top(): number {
    return this.values[this.values.length - 1];
  }

  getMin(): number {
    // A loop rather than Math.min(...values): spreading 10^5 arguments can overflow the call stack.
    let minimum = this.values[0];
    for (const value of this.values) {
      if (value < minimum) {
        minimum = value;
      }
    }
    return minimum;
  }
}
