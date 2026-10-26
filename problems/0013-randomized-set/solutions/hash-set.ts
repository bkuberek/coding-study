export class RandomizedSet {
  private readonly values = new Set<number>();

  insert(value: number): boolean {
    if (this.values.has(value)) {
      return false;
    }
    this.values.add(value);
    return true;
  }

  remove(value: number): boolean {
    // delete returns whether the value was present.
    return this.values.delete(value);
  }

  getRandom(): number {
    // A Set has no positions: walk its iteration order to a random rank, O(n).
    let rank = Math.floor(Math.random() * this.values.size);
    for (const value of this.values) {
      if (rank === 0) {
        return value;
      }
      rank--;
    }
    throw new Error("getRandom on an empty set");
  }
}
