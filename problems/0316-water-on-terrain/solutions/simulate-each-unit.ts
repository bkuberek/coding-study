const STAY = -1;
const SPILL = -2;

// Water is kept as a depth per column, and a column's level is its height plus its water.
//
// One unit of water is one walk: try to the left, then to the right, one column at a time and
// never uphill, and note where the final flat stretch of the walk begins. The walk either reaches
// an edge (the unit falls off), ends lower than it began (the unit settles at the start of the
// final flat stretch) or ends where it began (this direction does nothing).
export class Terrain {
  private readonly heights: number[];
  private readonly depths: number[];
  private spilledUnits = 0;

  constructor(heights: number[]) {
    this.heights = [...heights];
    this.depths = new Array<number>(heights.length).fill(0);
  }

  // Level 1
  render(): string[] {
    return this.picture(0, this.heights.length - 1);
  }

  tallest(): number {
    return this.heights.reduce((best, height) => Math.max(best, height), 0);
  }

  // Level 2
  pour(column: number): number[] {
    this.drop(column);
    return [...this.depths];
  }

  water(): number[] {
    return [...this.depths];
  }

  spilled(): number {
    return this.spilledUnits;
  }

  // Level 3
  pourMany(column: number, units: number): number[] {
    for (let unit = 0; unit < units; unit++) {
      this.drop(column);
    }
    return [...this.depths];
  }

  // Level 4
  renderWindow(first: number, last: number): string[] {
    return this.picture(first, last);
  }

  private level(column: number): number {
    return this.heights[column] + this.depths[column];
  }

  private drop(column: number): void {
    for (const step of [-1, 1]) {
      const landing = this.walk(column, step);
      if (landing === SPILL) {
        this.spilledUnits += 1;
        return;
      }
      if (landing !== STAY) {
        this.depths[landing] += 1;
        return;
      }
    }
    this.depths[column] += 1;
  }

  private walk(column: number, step: number): number {
    let at = column;
    let flatStart = column;
    for (;;) {
      const ahead = at + step;
      if (ahead < 0 || ahead >= this.heights.length) {
        return SPILL;
      }
      if (this.level(ahead) > this.level(at)) {
        break;
      }
      if (this.level(ahead) < this.level(at)) {
        flatStart = ahead;
      }
      at = ahead;
    }
    return this.level(flatStart) < this.level(column) ? flatStart : STAY;
  }

  private picture(first: number, last: number): string[] {
    let top = 0;
    for (let column = 0; column < this.heights.length; column++) {
      top = Math.max(top, this.level(column));
    }
    const rows: string[] = [];
    for (let row = top; row >= 1; row--) {
      let cells = "";
      for (let column = first; column <= last; column++) {
        if (this.heights[column] >= row) {
          cells += "#";
        } else if (this.level(column) >= row) {
          cells += "~";
        } else {
          cells += ".";
        }
      }
      rows.push(cells);
    }
    return rows;
  }
}
