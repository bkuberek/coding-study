export class RandomizedSet {
  private readonly values: number[] = [];

  insert(value: number): boolean {
    // includes() is a linear scan: O(n) per call.
    if (this.values.includes(value)) {
      return false;
    }
    this.values.push(value);
    return true;
  }

  remove(value: number): boolean {
    const index = this.values.indexOf(value);
    if (index === -1) {
      return false;
    }
    // Order does not matter: move the last value into the gap instead of shifting.
    const last = this.values.pop() as number;
    if (index < this.values.length) {
      this.values[index] = last;
    }
    return true;
  }

  getRandom(): number {
    return this.values[Math.floor(Math.random() * this.values.length)];
  }
}
