const COUNTED = 0;
const DUPLICATE = 1;
const RIVAL = 2;
const LOOP = 3;
const NONE = -1;

// Counted referrals form a forest: a person has at most one referrer.
//
// People are numbered in the order they first appear in a counted referral. The forest is kept
// in arrays (a referrer, a first and a last child, and a next sibling per person), a union-find
// answers "would this referral close a loop?" without walking up, and the totals are recounted
// in one breadth-first pass when a question needs them after a change. Nothing recurses, so a
// chain of 10^6 referrals is as safe as a flat one.
export class ReferralProgram {
  private readonly bonus: number;
  private readonly index = new Map<string, number>();
  private readonly names: string[] = [];
  private readonly referrer: number[] = [];
  private readonly first: number[] = [];
  private readonly last: number[] = [];
  private readonly next: number[] = [];
  private readonly direct: number[] = [];
  private readonly parentSet: number[] = [];
  private readonly setSize: number[] = [];
  private totals: number[] | null = [];

  constructor(bonus: number) {
    this.bonus = bonus;
  }

  // Level 1
  refer(referrer: string, referred: string): number {
    return this.apply(referrer, referred) === COUNTED ? this.bonus : 0;
  }

  points(person: string): number {
    const at = this.index.get(person);
    return at === undefined ? 0 : this.direct[at] * this.bonus;
  }

  referralsOf(person: string): string[] {
    const at = this.index.get(person);
    const found: string[] = [];
    let child = at === undefined ? NONE : this.first[at];
    while (child !== NONE) {
      found.push(this.names[child]);
      child = this.next[child];
    }
    return found;
  }

  // Level 2
  totalReferrals(person: string): number {
    const at = this.index.get(person);
    return at === undefined ? 0 : this.recount()[at];
  }

  topReferrer(): string {
    const best = this.leaderboard(1);
    return best.length > 0 ? best[0] : "";
  }

  // Level 3
  referAll(rows: string[][]): number[] {
    const tally = [0, 0, 0, 0];
    for (const [referrer, referred] of rows) {
      tally[this.apply(referrer, referred)] += 1;
    }
    return tally;
  }

  // Level 4
  leaderboard(k: number): string[] {
    const totals = this.recount();
    const ranked: number[] = [];
    for (let at = 0; at < totals.length; at++) {
      if (totals[at] > 0) {
        ranked.push(at);
      }
    }
    ranked.sort(
      (a, b) =>
        totals[b] - totals[a] ||
        this.direct[b] - this.direct[a] ||
        (this.names[a] < this.names[b] ? -1 : this.names[a] > this.names[b] ? 1 : 0),
    );
    return ranked.slice(0, k).map((at) => this.names[at]);
  }

  private person(name: string): number {
    let at = this.index.get(name);
    if (at === undefined) {
      at = this.names.length;
      this.index.set(name, at);
      this.names.push(name);
      this.referrer.push(NONE);
      this.first.push(NONE);
      this.last.push(NONE);
      this.next.push(NONE);
      this.direct.push(0);
      this.parentSet.push(at);
      this.setSize.push(1);
      this.totals = null;
    }
    return at;
  }

  private rootOf(start: number): number {
    let at = start;
    while (this.parentSet[at] !== at) {
      this.parentSet[at] = this.parentSet[this.parentSet[at]];
      at = this.parentSet[at];
    }
    return at;
  }

  private apply(referrer: string, referred: string): number {
    if (referrer === referred) {
      return LOOP;
    }
    const known = this.index.get(referred);
    if (known !== undefined && this.referrer[known] !== NONE) {
      return this.names[this.referrer[known]] === referrer ? DUPLICATE : RIVAL;
    }
    const above = this.person(referrer);
    const below = this.person(referred);
    let top = this.rootOf(above);
    let bottom = this.rootOf(below);
    if (top === bottom) {
      return LOOP;
    }
    if (this.setSize[top] < this.setSize[bottom]) {
      [top, bottom] = [bottom, top];
    }
    this.parentSet[bottom] = top;
    this.setSize[top] += this.setSize[bottom];
    this.referrer[below] = above;
    if (this.first[above] === NONE) {
      this.first[above] = below;
    } else {
      this.next[this.last[above]] = below;
    }
    this.last[above] = below;
    this.direct[above] += 1;
    this.totals = null;
    return COUNTED;
  }

  private recount(): number[] {
    if (this.totals !== null) {
      return this.totals;
    }
    const count = this.names.length;
    const order: number[] = [];
    for (let at = 0; at < count; at++) {
      if (this.referrer[at] === NONE) {
        order.push(at);
      }
    }
    for (let seen = 0; seen < order.length; seen++) {
      let child = this.first[order[seen]];
      while (child !== NONE) {
        order.push(child);
        child = this.next[child];
      }
    }
    const totals = new Array<number>(count).fill(0);
    for (let seen = order.length - 1; seen >= 0; seen--) {
      const above = this.referrer[order[seen]];
      if (above !== NONE) {
        totals[above] += totals[order[seen]] + 1;
      }
    }
    this.totals = totals;
    return totals;
  }
}
