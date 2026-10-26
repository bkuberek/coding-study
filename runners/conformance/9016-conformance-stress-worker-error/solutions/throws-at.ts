export class StressFailer {
  step(index: number): number {
    if (index === 100) {
      throw new Error("failed at 100");
    }
    return index;
  }
}
