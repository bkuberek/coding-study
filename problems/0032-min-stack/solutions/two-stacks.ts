export class MinStack {
  private readonly values: number[] = [];
  // The minimums in the order they took effect; the last one is the current minimum.
  private readonly minimums: number[] = [];

  push(value: number): void {
    this.values.push(value);
    // <= keeps one copy per equal minimum, so popping one copy keeps the others.
    if (this.minimums.length === 0 || value <= this.minimums[this.minimums.length - 1]) {
      this.minimums.push(value);
    }
  }

  pop(): void {
    if (this.values.pop() === this.minimums[this.minimums.length - 1]) {
      this.minimums.pop();
    }
  }

  top(): number {
    return this.values[this.values.length - 1];
  }

  getMin(): number {
    return this.minimums[this.minimums.length - 1];
  }
}
