export class Counter {
  count = 0;

  increment(): number {
    this.count += 1;
    return this.count;
  }

  fail(): number {
    throw new Error("counter failure");
  }
}
