interface Write {
  index: number;
  value: number;
  snapsBefore: number; // snapshots taken before this write
}

export class SnapshotArray {
  private readonly log: Write[] = [];
  private snaps = 0;

  constructor(_length: number) {}

  set(index: number, value: number): void {
    this.log.push({ index, value, snapsBefore: this.snaps });
  }

  snap(): number {
    return this.snaps++;
  }

  get(index: number, snapId: number): number {
    // The newest write to index that happened before snapshot snapId was taken.
    for (let i = this.log.length - 1; i >= 0; i--) {
      const write = this.log[i];
      if (write.index === index && write.snapsBefore <= snapId) {
        return write.value;
      }
    }
    return 0;
  }
}
