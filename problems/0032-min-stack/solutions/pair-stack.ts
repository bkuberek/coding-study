export class MinStack {
  // values[i] and minimums[i] together form entry i: a value and the minimum at or below it.
  private readonly values: number[] = [];
  private readonly minimums: number[] = [];

  push(value: number): void {
    const below = this.minimums.length === 0 ? value : this.minimums[this.minimums.length - 1];
    this.values.push(value);
    this.minimums.push(Math.min(value, below));
  }

  pop(): void {
    this.values.pop();
    this.minimums.pop();
  }

  top(): number {
    return this.values[this.values.length - 1];
  }

  getMin(): number {
    return this.minimums[this.minimums.length - 1];
  }
}
