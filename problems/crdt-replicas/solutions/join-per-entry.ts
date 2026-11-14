// One replica's slot of a counter: what it added (`up`) and what it took away (`down`), each with
// the change number at which it last grew.
interface Slot {
  up: number;
  upAt: number;
  down: number;
  downAt: number;
}

interface Register {
  text: string;
  timestamp: number;
  writer: string;
  at: number;
}

interface Tag {
  addedAt: number;
  removed: boolean;
  removedAt: number;
}

function beats(timestamp: number, writer: string, current: Register): boolean {
  if (timestamp !== current.timestamp) return timestamp > current.timestamp;
  return writer > current.writer;
}

function child<K, V>(map: Map<K, V>, key: K, make: () => V): V {
  let found = map.get(key);
  if (found === undefined) {
    found = make();
    map.set(key, found);
  }
  return found;
}

// The whole state of one replica. Every entry (a counter slot's up or down part, a register, an
// add tag, a tombstone) only grows, and each one remembers the change number at which it last
// grew, so a sync can pick the entries that changed after the last acknowledgement.
class Replica {
  clock = 0;
  adds = 0;
  readonly counters = new Map<string, Map<string, Slot>>();
  readonly registers = new Map<string, Register>();
  readonly sets = new Map<string, Map<string, Map<string, Tag>>>();
  readonly acked = new Map<string, number>();

  tick(): number {
    this.clock += 1;
    return this.clock;
  }

  slot(counter: string, owner: string): Slot {
    const slots = child(this.counters, counter, () => new Map<string, Slot>());
    return child(slots, owner, () => ({ up: 0, upAt: 0, down: 0, downAt: 0 }));
  }

  total(counter: string): number {
    let sum = 0;
    for (const slot of this.counters.get(counter)?.values() ?? []) sum += slot.up - slot.down;
    return sum;
  }

  tags(setName: string, element: string): Map<string, Tag> {
    const elements = child(this.sets, setName, () => new Map<string, Map<string, Tag>>());
    return child(elements, element, () => new Map<string, Tag>());
  }

  live(setName: string, element: string): boolean {
    for (const tag of this.sets.get(setName)?.get(element)?.values() ?? []) {
      if (!tag.removed) return true;
    }
    return false;
  }

  size(): number {
    let count = this.registers.size;
    for (const slots of this.counters.values()) {
      for (const slot of slots.values()) count += (slot.up > 0 ? 1 : 0) + (slot.down > 0 ? 1 : 0);
    }
    for (const elements of this.sets.values()) {
      for (const tags of elements.values()) {
        for (const tag of tags.values()) count += tag.removed ? 2 : 1;
      }
    }
    return count;
  }

  // Joins every entry of `source` that changed after `since` into this replica and returns how
  // many entries that was. `since = 0` is a full-state merge.
  absorb(source: Replica, since: number): number {
    let sent = 0;
    for (const [counter, slots] of source.counters) {
      for (const [owner, theirs] of slots) {
        const mine = this.slot(counter, owner);
        if (theirs.up > 0 && theirs.upAt > since) {
          sent += 1;
          if (theirs.up > mine.up) {
            mine.up = theirs.up;
            mine.upAt = this.tick();
          }
        }
        if (theirs.down > 0 && theirs.downAt > since) {
          sent += 1;
          if (theirs.down > mine.down) {
            mine.down = theirs.down;
            mine.downAt = this.tick();
          }
        }
      }
    }
    for (const [name, theirs] of source.registers) {
      if (theirs.at <= since) continue;
      sent += 1;
      const mine = this.registers.get(name);
      if (mine === undefined || beats(theirs.timestamp, theirs.writer, mine)) {
        this.registers.set(name, { ...theirs, at: this.tick() });
      }
    }
    for (const [setName, elements] of source.sets) {
      for (const [element, tags] of elements) {
        const mine = this.tags(setName, element);
        for (const [tag, theirs] of tags) sent += this.absorbTag(mine, tag, theirs, since);
      }
    }
    return sent;
  }

  private absorbTag(mine: Map<string, Tag>, tag: string, theirs: Tag, since: number): number {
    let sent = 0;
    if (theirs.addedAt > since) {
      sent += 1;
      if (!mine.has(tag)) mine.set(tag, { addedAt: this.tick(), removed: false, removedAt: 0 });
    }
    if (theirs.removed && theirs.removedAt > since) {
      sent += 1;
      const held = child(mine, tag, () => ({ addedAt: this.tick(), removed: false, removedAt: 0 }));
      if (!held.removed) {
        held.removed = true;
        held.removedAt = this.tick();
      }
    }
    return sent;
  }
}

// A group of replicas of the same data. Each replica's state is a set of entries that only grow,
// and merging is taking the larger value of every entry, so merges can happen in any order, any
// number of times, and replicas that have seen the same updates hold the same state.
export class Replicas {
  private readonly replicas = new Map<string, Replica>();

  constructor(ids: string[]) {
    for (const id of ids) this.replicas.set(id, new Replica());
  }

  private at(name: string): Replica {
    return this.replicas.get(name)!;
  }

  // Level 1
  increment(replica: string, counter: string, amount: number): number {
    const node = this.at(replica);
    const slot = node.slot(counter, replica);
    slot.up += amount;
    slot.upAt = node.tick();
    return node.total(counter);
  }

  decrement(replica: string, counter: string, amount: number): number {
    const node = this.at(replica);
    const slot = node.slot(counter, replica);
    slot.down += amount;
    slot.downAt = node.tick();
    return node.total(counter);
  }

  value(replica: string, counter: string): number {
    return this.at(replica).total(counter);
  }

  merge(source: string, target: string): void {
    this.at(target).absorb(this.at(source), 0);
  }

  // Level 2
  write(replica: string, register: string, text: string, timestamp: number): boolean {
    const node = this.at(replica);
    const current = node.registers.get(register);
    if (current !== undefined && !beats(timestamp, replica, current)) return false;
    node.registers.set(register, { text, timestamp, writer: replica, at: node.tick() });
    return true;
  }

  read(replica: string, register: string): string {
    return this.at(replica).registers.get(register)?.text ?? "";
  }

  // Level 3
  add(replica: string, setName: string, element: string): string {
    const node = this.at(replica);
    node.adds += 1;
    const tag = `${replica}:${node.adds}`;
    node.tags(setName, element).set(tag, { addedAt: node.tick(), removed: false, removedAt: 0 });
    return tag;
  }

  remove(replica: string, setName: string, element: string): number {
    const node = this.at(replica);
    let removed = 0;
    for (const tag of node.sets.get(setName)?.get(element)?.values() ?? []) {
      if (tag.removed) continue;
      tag.removed = true;
      tag.removedAt = node.tick();
      removed += 1;
    }
    return removed;
  }

  contains(replica: string, setName: string, element: string): boolean {
    return this.at(replica).live(setName, element);
  }

  elements(replica: string, setName: string): string[] {
    const node = this.at(replica);
    const present = [...(node.sets.get(setName)?.keys() ?? [])].filter((e) => node.live(setName, e));
    return present.sort((x, y) => (x < y ? -1 : x > y ? 1 : 0));
  }

  // Level 4
  sync(source: string, target: string): number {
    const sender = this.at(source);
    const sent = this.at(target).absorb(sender, sender.acked.get(target) ?? 0);
    sender.acked.set(target, sender.clock);
    return sent;
  }

  stateSize(replica: string): number {
    return this.at(replica).size();
  }
}
