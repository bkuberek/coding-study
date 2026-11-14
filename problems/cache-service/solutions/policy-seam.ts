// Tracks the live keys and names the one to evict when the cache is full.
interface EvictionPolicy {
  admit(key: string): void;
  touch(key: string): void;
  forget(key: string): void;
  victim(): string | undefined;
}

class LruPolicy implements EvictionPolicy {
  protected readonly order = new Set<string>(); // least recently used first

  admit(key: string): void {
    this.order.add(key);
  }

  touch(key: string): void {
    this.order.delete(key);
    this.order.add(key);
  }

  forget(key: string): void {
    this.order.delete(key);
  }

  victim(): string | undefined {
    return this.order.values().next().value;
  }
}

class FifoPolicy extends LruPolicy {
  // Using a key does not change its place: the oldest insertion goes first.
  override touch(key: string): void {}
}

// Least frequently used first; among equal counts, least recently used first.
class LfuPolicy implements EvictionPolicy {
  private readonly counts = new Map<string, number>();
  private readonly buckets = new Map<number, Set<string>>();
  private lowest = 1; // never above the lowest count in use

  admit(key: string): void {
    this.place(key, 1);
    this.lowest = 1;
  }

  touch(key: string): void {
    const count = this.counts.get(key) ?? 1;
    this.buckets.get(count)?.delete(key);
    this.place(key, count + 1);
  }

  forget(key: string): void {
    this.buckets.get(this.counts.get(key) ?? 1)?.delete(key);
    this.counts.delete(key);
  }

  victim(): string | undefined {
    if (this.counts.size === 0) {
      return undefined;
    }
    while ((this.buckets.get(this.lowest)?.size ?? 0) === 0) {
      this.lowest++;
    }
    return this.buckets.get(this.lowest)?.values().next().value;
  }

  private place(key: string, count: number): void {
    this.counts.set(key, count);
    let bucket = this.buckets.get(count);
    if (bucket === undefined) {
      bucket = new Set();
      this.buckets.set(count, bucket);
    }
    bucket.add(key);
  }
}

const POLICIES = new Map<string, () => EvictionPolicy>([
  ["LRU", () => new LruPolicy()],
  ["LFU", () => new LfuPolicy()],
  ["FIFO", () => new FifoPolicy()],
]);

class Entry {
  value: string;
  expiresAt: number | null;

  constructor(value: string, expiresAt: number | null) {
    this.value = value;
    this.expiresAt = expiresAt;
  }

  expired(now: number): boolean {
    return this.expiresAt !== null && now >= this.expiresAt;
  }
}

// A binary min-heap of [expiresAt, key] pairs.
class ExpiryHeap {
  private readonly items: [number, string][] = [];

  push(item: [number, string]): void {
    const items = this.items;
    items.push(item);
    for (let child = items.length - 1; child > 0; ) {
      const parent = (child - 1) >> 1;
      if (items[parent][0] <= items[child][0]) {
        break;
      }
      [items[parent], items[child]] = [items[child], items[parent]];
      child = parent;
    }
  }

  peek(): [number, string] | undefined {
    return this.items[0];
  }

  pop(): void {
    const items = this.items;
    const last = items.pop();
    if (last === undefined || items.length === 0) {
      return;
    }
    items[0] = last;
    for (let parent = 0; ; ) {
      const left = 2 * parent + 1;
      const right = left + 1;
      let smallest = parent;
      if (left < items.length && items[left][0] < items[smallest][0]) {
        smallest = left;
      }
      if (right < items.length && items[right][0] < items[smallest][0]) {
        smallest = right;
      }
      if (smallest === parent) {
        return;
      }
      [items[parent], items[smallest]] = [items[smallest], items[parent]];
      parent = smallest;
    }
  }
}

export class CacheService {
  private readonly capacity: number;
  private readonly policy: EvictionPolicy;
  private readonly entries = new Map<string, Entry>();
  private readonly expiries = new ExpiryHeap(); // stale pairs are skipped
  private hits = 0;
  private misses = 0;
  private evictions = 0;
  private expirations = 0;

  constructor(capacity: number, policy: string) {
    this.capacity = capacity;
    this.policy = (POLICIES.get(policy) ?? (() => new LruPolicy()))();
  }

  put(timestamp: number, key: string, value: string, ttl: number): void {
    const expiresAt = ttl > 0 ? timestamp + ttl : null;
    const entry = this.live(timestamp, key);
    if (entry !== undefined) {
      entry.value = value;
      entry.expiresAt = expiresAt;
      this.policy.touch(key);
    } else {
      this.makeRoom(timestamp);
      this.entries.set(key, new Entry(value, expiresAt));
      this.policy.admit(key);
    }
    if (expiresAt !== null) {
      this.expiries.push([expiresAt, key]);
    }
  }

  get(timestamp: number, key: string): string {
    const entry = this.live(timestamp, key);
    if (entry === undefined) {
      this.misses++;
      return "";
    }
    this.hits++;
    this.policy.touch(key);
    return entry.value;
  }

  remove(timestamp: number, key: string): boolean {
    if (this.live(timestamp, key) === undefined) {
      return false;
    }
    this.drop(key);
    return true;
  }

  size(timestamp: number): number {
    this.purgeExpired(timestamp);
    return this.entries.size;
  }

  stats(): number[] {
    return [this.hits, this.misses, this.evictions, this.expirations];
  }

  private live(now: number, key: string): Entry | undefined {
    const entry = this.entries.get(key);
    if (entry !== undefined && entry.expired(now)) {
      this.expire(key);
      return undefined;
    }
    return entry;
  }

  private makeRoom(now: number): void {
    if (this.entries.size < this.capacity) {
      return;
    }
    this.purgeExpired(now);
    const victim = this.entries.size >= this.capacity ? this.policy.victim() : undefined;
    if (victim !== undefined) {
      this.drop(victim);
      this.evictions++;
    }
  }

  private purgeExpired(now: number): void {
    for (let top = this.expiries.peek(); top !== undefined && top[0] <= now; top = this.expiries.peek()) {
      this.expiries.pop();
      const [expiresAt, key] = top;
      if (this.entries.get(key)?.expiresAt === expiresAt) {
        this.expire(key);
      }
    }
  }

  private expire(key: string): void {
    this.drop(key);
    this.expirations++;
  }

  private drop(key: string): void {
    this.entries.delete(key);
    this.policy.forget(key);
  }
}
