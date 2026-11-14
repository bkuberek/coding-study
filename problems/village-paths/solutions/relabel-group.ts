export class VillageMap {
  private readonly label: number[]; // label[v]: the name of the group of village v
  private readonly members: number[]; // members[g]: how many villages carry label g
  private groups: number;

  constructor(villages: number) {
    this.label = Array.from({ length: villages }, (_, village) => village);
    this.members = new Array<number>(villages).fill(1);
    this.groups = villages;
  }

  addPath(a: number, b: number): boolean {
    const keep = this.label[a];
    const drop = this.label[b];
    if (keep === drop) {
      return false;
    }
    // Every village of the dropped group has to learn its new label.
    for (let village = 0; village < this.label.length; village++) {
      if (this.label[village] === drop) {
        this.label[village] = keep;
      }
    }
    this.members[keep] += this.members[drop];
    this.groups--;
    return true;
  }

  canReach(a: number, b: number): boolean {
    return this.label[a] === this.label[b];
  }

  groupSize(village: number): number {
    return this.members[this.label[village]];
  }

  groupCount(): number {
    return this.groups;
  }
}
