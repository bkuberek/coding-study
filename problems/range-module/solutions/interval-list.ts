export class RangeModule {
  // Disjoint, non-touching half-open intervals [starts[i], ends[i]), sorted by start.
  // Two arrays of small integers instead of an array of pairs: no allocation per interval.
  private starts: number[] = [];
  private ends: number[] = [];

  constructor() {}

  addRange(left: number, right: number): void {
    const starts: number[] = [];
    const ends: number[] = [];
    let placed = false;
    for (let i = 0; i < this.starts.length; i++) {
      const start = this.starts[i];
      const end = this.ends[i];
      if (end < left) {
        starts.push(start);
        ends.push(end);
      } else if (right < start) {
        if (!placed) {
          starts.push(left);
          ends.push(right);
          placed = true;
        }
        starts.push(start);
        ends.push(end);
      } else {
        // Overlapping or touching: absorb it into the new interval.
        left = Math.min(left, start);
        right = Math.max(right, end);
      }
    }
    if (!placed) {
      starts.push(left);
      ends.push(right);
    }
    this.starts = starts;
    this.ends = ends;
  }

  queryRange(left: number, right: number): boolean {
    // Stored intervals never touch, so a covered range lies inside a single one.
    for (let i = 0; i < this.starts.length; i++) {
      if (this.starts[i] <= left && right <= this.ends[i]) {
        return true;
      }
    }
    return false;
  }

  removeRange(left: number, right: number): void {
    const starts: number[] = [];
    const ends: number[] = [];
    for (let i = 0; i < this.starts.length; i++) {
      const start = this.starts[i];
      const end = this.ends[i];
      if (end <= left || right <= start) {
        starts.push(start);
        ends.push(end);
        continue;
      }
      if (start < left) {
        starts.push(start);
        ends.push(left);
      }
      if (right < end) {
        starts.push(right);
        ends.push(end);
      }
    }
    this.starts = starts;
    this.ends = ends;
  }
}
