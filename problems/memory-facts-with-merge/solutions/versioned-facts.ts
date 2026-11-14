const REFERENCE_MARK = "@";

// One version of a fact: its number in this store, the time it was remembered, its value.
interface Fact {
  readonly number: number;
  readonly time: number;
  readonly value: string;
}

function factId(number: number): string {
  return `f${number}`;
}

// A subject and an attribute name a fact within one user. Neither holds a space.
function keyOf(subject: string, attribute: string): string {
  return `${subject} ${attribute}`;
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

// Every version of one subject and attribute, oldest first; times never decrease.
class History {
  readonly subject: string;
  readonly attribute: string;
  readonly facts: Fact[] = [];

  constructor(subject: string, attribute: string) {
    this.subject = subject;
    this.attribute = attribute;
  }

  get current(): Fact {
    return this.facts[this.facts.length - 1];
  }

  inForceAt(moment: number): Fact | null {
    let low = 0;
    let high = this.facts.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (this.facts[middle].time <= moment) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    return low === 0 ? null : this.facts[low - 1];
  }
}

function replaces(incoming: Fact, held: History | undefined, incomingWinsTies: boolean): boolean {
  if (held === undefined) {
    return true;
  }
  if (incoming.time !== held.current.time) {
    return incoming.time > held.current.time;
  }
  return incomingWinsTies;
}

// The value with a reference to an imported id pointed at that fact's new id.
function follow(value: string, newIds: Map<string, string>): string {
  const target = value.startsWith(REFERENCE_MARK) ? newIds.get(value.slice(1)) : undefined;
  return target === undefined ? value : REFERENCE_MARK + target;
}

function bySubjectThenAttribute(a: History, b: History): number {
  return compareText(a.subject, b.subject) || compareText(a.attribute, b.attribute);
}

export class FactMemory {
  private readonly users = new Map<string, Map<string, History>>();
  private readonly priorities = new Map<string, number>();
  private lastNumber = 0;

  // Level 1
  remember(timestamp: number, user: string, subject: string, attribute: string, value: string): string {
    return factId(this.add(user, subject, attribute, { number: this.nextNumber(), time: timestamp, value }));
  }

  recall(timestamp: number, user: string, subject: string, attribute: string): string {
    return this.historyOf(user, subject, attribute)?.current.value ?? "";
  }

  listFacts(timestamp: number, user: string): string[] {
    return this.sortedHistories(user).map((history) => `${history.subject}.${history.attribute}=${history.current.value}`);
  }

  // Level 2
  recallAt(timestamp: number, user: string, subject: string, attribute: string, at: number): string {
    return this.historyOf(user, subject, attribute)?.inForceAt(at)?.value ?? "";
  }

  history(timestamp: number, user: string, subject: string, attribute: string): string[] {
    const facts = this.historyOf(user, subject, attribute)?.facts ?? [];
    return facts.map((fact) => `${factId(fact.number)}@${fact.time}=${fact.value}`);
  }

  // Level 3
  setPriority(timestamp: number, user: string, priority: number): void {
    this.priorities.set(user, priority);
  }

  merge(timestamp: number, fromUser: string, intoUser: string): number {
    const held = this.users.get(intoUser) ?? new Map<string, History>();
    const incomingWinsTies = this.priorityOf(fromUser) > this.priorityOf(intoUser);
    const taken = this.sortedHistories(fromUser).filter((history) =>
      replaces(history.current, held.get(keyOf(history.subject, history.attribute)), incomingWinsTies),
    );
    for (const { subject, attribute, current } of taken) {
      this.add(intoUser, subject, attribute, { number: this.nextNumber(), time: current.time, value: current.value });
    }
    return taken.length;
  }

  // Level 4
  exportFacts(timestamp: number, user: string): string[] {
    const versions: [Fact, History][] = [];
    for (const history of this.users.get(user)?.values() ?? []) {
      for (const fact of history.facts) {
        versions.push([fact, history]);
      }
    }
    versions.sort(([a], [b]) => a.number - b.number);
    return versions.map(
      ([fact, { subject, attribute }]) => `${factId(fact.number)} ${fact.time} ${subject} ${attribute} ${fact.value}`,
    );
  }

  importFacts(timestamp: number, user: string, lines: string[]): string[] {
    if ((this.users.get(user)?.size ?? 0) > 0) {
      return [];
    }
    const rows = lines.map((line) => line.split(" "));
    // Every new number is given out before any value is rewritten, so a reference may
    // name a line further down.
    const newNumbers = new Map(rows.map(([oldId]) => [oldId, this.nextNumber()]));
    const newIds = new Map([...newNumbers].map(([oldId, number]) => [oldId, factId(number)]));
    for (const [oldId, time, subject, attribute, value] of rows) {
      this.add(user, subject, attribute, { number: newNumbers.get(oldId)!, time: Number(time), value: follow(value, newIds) });
    }
    return rows.map(([oldId]) => newIds.get(oldId)!);
  }

  private add(user: string, subject: string, attribute: string, fact: Fact): number {
    let histories = this.users.get(user);
    if (histories === undefined) {
      histories = new Map();
      this.users.set(user, histories);
    }
    const key = keyOf(subject, attribute);
    let history = histories.get(key);
    if (history === undefined) {
      history = new History(subject, attribute);
      histories.set(key, history);
    }
    history.facts.push(fact);
    return fact.number;
  }

  private nextNumber(): number {
    this.lastNumber += 1;
    return this.lastNumber;
  }

  private historyOf(user: string, subject: string, attribute: string): History | undefined {
    return this.users.get(user)?.get(keyOf(subject, attribute));
  }

  private sortedHistories(user: string): History[] {
    return [...(this.users.get(user)?.values() ?? [])].sort(bySubjectThenAttribute);
  }

  private priorityOf(user: string): number {
    return this.priorities.get(user) ?? 0;
  }
}
