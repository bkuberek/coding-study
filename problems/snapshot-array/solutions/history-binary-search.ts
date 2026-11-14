export class SnapshotArray {
  // For each position, parallel lists: the snapshot ids at which it changed (strictly
  // increasing) and the value it held from that snapshot on.
  private readonly ids: number[][];
  private readonly values: number[][];
  private snaps = 0;

  constructor(length: number) {
    this.ids = Array.from({ length }, () => []);
    this.values = Array.from({ length }, () => []);
  }

  set(index: number, value: number): void {
    const ids = this.ids[index];
    const last = ids.length - 1;
    if (last >= 0 && ids[last] === this.snaps) {
      this.values[index][last] = value; // overwrite within the same snapshot
    } else {
      ids.push(this.snaps);
      this.values[index].push(value);
    }
  }

  snap(): number {
    return this.snaps++;
  }

  get(index: number, snapId: number): number {
    // Upper bound: how many changes happened at or before snapId.
    const ids = this.ids[index];
    let low = 0;
    let high = ids.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (ids[middle] <= snapId) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    return low > 0 ? this.values[index][low - 1] : 0;
  }
}
