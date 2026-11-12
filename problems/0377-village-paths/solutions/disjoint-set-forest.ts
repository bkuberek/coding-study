export class VillageMap {
  private readonly parent: number[]; // parent[v] === v marks the leader of a group
  private readonly size: number[]; // size[r]: villages in the group whose leader is r
  private groups: number;

  constructor(villages: number) {
    this.parent = Array.from({ length: villages }, (_, village) => village);
    this.size = new Array<number>(villages).fill(1);
    this.groups = villages;
  }

  private leader(start: number): number {
    let root = start;
    while (this.parent[root] !== root) {
      root = this.parent[root];
    }
    // Path compression: send everything passed on the way straight to the leader.
    let village = start;
    while (this.parent[village] !== root) {
      const next = this.parent[village];
      this.parent[village] = root;
      village = next;
    }
    return root;
  }

  addPath(a: number, b: number): boolean {
    let leaderA = this.leader(a);
    let leaderB = this.leader(b);
    if (leaderA === leaderB) {
      return false;
    }
    if (this.size[leaderA] < this.size[leaderB]) {
      [leaderA, leaderB] = [leaderB, leaderA];
    }
    this.parent[leaderB] = leaderA; // union by size: the smaller group joins the larger
    this.size[leaderA] += this.size[leaderB];
    this.groups--;
    return true;
  }

  canReach(a: number, b: number): boolean {
    return this.leader(a) === this.leader(b);
  }

  groupSize(village: number): number {
    return this.size[this.leader(village)];
  }

  groupCount(): number {
    return this.groups;
  }
}
