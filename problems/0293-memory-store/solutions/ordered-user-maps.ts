// Plain string order, as in the other language; localeCompare would not match it.
function compareIds(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

// One memory: its texts so far (the last is current), its write time and its expiry.
class Memory {
  readonly versions: string[];
  readonly expiresAt: number | null;
  words: Set<string>;
  writtenAt: number;

  constructor(text: string, writtenAt: number, expiresAt: number | null) {
    this.versions = [text];
    this.words = new Set(text.split(" "));
    this.writtenAt = writtenAt;
    this.expiresAt = expiresAt;
  }

  isLiveAt(moment: number): boolean {
    return this.expiresAt === null || moment < this.expiresAt;
  }

  write(text: string, moment: number): void {
    this.versions.push(text);
    this.words = new Set(text.split(" "));
    this.writtenAt = moment;
  }

  get text(): string {
    return this.versions[this.versions.length - 1];
  }
}

export class MemoryStore {
  // Each user's memories, least recently used first: a Map iterates in insertion order.
  private readonly users = new Map<string, Map<string, Memory>>();
  private readonly quotas = new Map<string, number>();

  // Level 1
  add(timestamp: number, userId: string, memoryId: string, text: string): boolean {
    return this.insert(timestamp, userId, memoryId, new Memory(text, timestamp, null));
  }

  get(timestamp: number, userId: string, memoryId: string): string {
    return this.use(timestamp, userId, memoryId)?.text ?? "";
  }

  update(timestamp: number, userId: string, memoryId: string, text: string): boolean {
    const memory = this.use(timestamp, userId, memoryId);
    if (memory === null) {
      return false;
    }
    memory.write(text, timestamp);
    return true;
  }

  remove(timestamp: number, userId: string, memoryId: string): boolean {
    if (this.live(timestamp, userId, memoryId) === null) {
      return false;
    }
    this.users.get(userId)!.delete(memoryId);
    return true;
  }

  // Level 2
  search(timestamp: number, userId: string, query: string, k: number): string[] {
    const terms = new Set(query.split(" "));
    const ranked: { id: string; matched: number; writtenAt: number }[] = [];
    for (const [id, memory] of this.users.get(userId) ?? []) {
      let matched = 0;
      for (const term of terms) {
        if (memory.words.has(term)) {
          matched += 1;
        }
      }
      if (matched > 0 && memory.isLiveAt(timestamp)) {
        ranked.push({ id, matched, writtenAt: memory.writtenAt });
      }
    }
    ranked.sort(
      (a, b) => b.matched - a.matched || b.writtenAt - a.writtenAt || compareIds(a.id, b.id),
    );
    return ranked.slice(0, k).map((entry) => entry.id);
  }

  // Level 3
  addWithTtl(
    timestamp: number,
    userId: string,
    memoryId: string,
    text: string,
    ttl: number,
  ): boolean {
    return this.insert(timestamp, userId, memoryId, new Memory(text, timestamp, timestamp + ttl));
  }

  // Level 4
  history(timestamp: number, userId: string, memoryId: string): string[] {
    return [...(this.live(timestamp, userId, memoryId)?.versions ?? [])];
  }

  rollback(timestamp: number, userId: string, memoryId: string, version: number): boolean {
    const memory = this.live(timestamp, userId, memoryId);
    if (memory === null || version < 1 || version >= memory.versions.length) {
      return false;
    }
    this.markUsed(userId, memoryId, memory);
    memory.write(memory.versions[version - 1], timestamp);
    return true;
  }

  setQuota(timestamp: number, userId: string, limit: number): string[] {
    this.quotas.set(userId, limit);
    return this.evictDownTo(timestamp, userId, limit);
  }

  // The memory if it exists and has not expired; an expired one is dropped for good.
  private live(timestamp: number, userId: string, memoryId: string): Memory | null {
    const memories = this.users.get(userId);
    const memory = memories?.get(memoryId);
    if (memories === undefined || memory === undefined) {
      return null;
    }
    if (!memory.isLiveAt(timestamp)) {
      memories.delete(memoryId);
      return null;
    }
    return memory;
  }

  // `live`, and marks the memory as the user's most recently used one.
  private use(timestamp: number, userId: string, memoryId: string): Memory | null {
    const memory = this.live(timestamp, userId, memoryId);
    if (memory !== null) {
      this.markUsed(userId, memoryId, memory);
    }
    return memory;
  }

  private markUsed(userId: string, memoryId: string, memory: Memory): void {
    const memories = this.users.get(userId)!;
    memories.delete(memoryId);
    memories.set(memoryId, memory);
  }

  private insert(timestamp: number, userId: string, memoryId: string, memory: Memory): boolean {
    if (this.live(timestamp, userId, memoryId) !== null) {
      return false;
    }
    const quota = this.quotas.get(userId);
    if (quota !== undefined) {
      this.evictDownTo(timestamp, userId, quota - 1);
    }
    let memories = this.users.get(userId);
    if (memories === undefined) {
      memories = new Map();
      this.users.set(userId, memories);
    }
    memories.set(memoryId, memory);
    return true;
  }

  // Drops the user's expired memories, then the least recently used live ones until `size` remain.
  private evictDownTo(timestamp: number, userId: string, size: number): string[] {
    const memories = this.users.get(userId);
    if (memories === undefined) {
      return [];
    }
    for (const [id, memory] of memories) {
      if (!memory.isLiveAt(timestamp)) {
        memories.delete(id);
      }
    }
    const evicted: string[] = [];
    for (const id of memories.keys()) {
      if (memories.size <= size) {
        break;
      }
      memories.delete(id);
      evicted.push(id);
    }
    return evicted;
  }
}
