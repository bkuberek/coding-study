export class RandomizedSet {
  private readonly values: number[] = [];
  private readonly indexOf = new Map<number, number>();

  insert(value: number): boolean {
    if (this.indexOf.has(value)) {
      return false;
    }
    this.indexOf.set(value, this.values.length);
    this.values.push(value);
    return true;
  }

  remove(value: number): boolean {
    const index = this.indexOf.get(value);
    if (index === undefined) {
      return false;
    }
    this.indexOf.delete(value);
    const last = this.values.pop() as number;
    if (index < this.values.length) {
      // Fill the gap with the former last value and record its new position.
      this.values[index] = last;
      this.indexOf.set(last, index);
    }
    return true;
  }

  getRandom(): number {
    return this.values[Math.floor(Math.random() * this.values.length)];
  }
}
