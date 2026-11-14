// One address space: a page table from page to frame, an optional TLB kept in least-recently-used
// order, and, once demand paging is on, a frame table with the state each replacement policy
// needs: the load order for FIFO, the use order for LRU, and a use bit per frame and a hand for
// the clock. Every translation is one reference in a history, which the working set reads.
//
// Addresses reach 2^48, beyond the 32 bits of JavaScript's bitwise operators, so the address is
// split with division and remainder, which are exact for integers below 2^53.

export class VirtualMemory {
  private size: number;
  private table = new Map<number, number>();
  private faultCount = 0;
  private tlb: Map<number, number> | null = null;
  private tlbEntries = 0;
  private hits = 0;
  private misses = 0;
  private frames = 0;
  private policy = "";
  private owner: number[] = [];
  private loaded = new Set<number>();
  private recent = new Set<number>();
  private use: boolean[] = [];
  private hand = 0;
  private history: number[] = [];

  constructor(pageSize: number) {
    this.size = pageSize;
  }

  // Level 1
  split(address: number): number[] {
    return [Math.floor(address / this.size), address % this.size];
  }

  mapPage(page: number, frame: number): boolean {
    const isNew = !this.table.has(page);
    this.table.set(page, frame);
    this.tlb?.delete(page);
    return isNew;
  }

  unmapPage(page: number): boolean {
    if (!this.table.delete(page)) return false;
    this.tlb?.delete(page);
    return true;
  }

  translate(address: number): number {
    const [page, offset] = this.split(address);
    this.history.push(page);
    const frame = this.frameOf(page);
    return frame === null ? -1 : frame * this.size + offset;
  }

  faults(): number {
    return this.faultCount;
  }

  // Level 2
  enableTlb(entries: number): void {
    this.tlb = new Map();
    this.tlbEntries = entries;
    this.hits = 0;
    this.misses = 0;
  }

  flushTlb(): void {
    this.tlb?.clear();
  }

  tlbHits(): number {
    return this.hits;
  }

  tlbMisses(): number {
    return this.misses;
  }

  // Level 3
  useFrames(count: number, policy: string): void {
    this.frames = count;
    this.policy = policy;
    this.table.clear();
    this.flushTlb();
    this.faultCount = 0;
    this.hits = 0;
    this.misses = 0;
    this.owner = new Array(count).fill(-1);
    this.use = new Array(count).fill(false);
    this.loaded.clear();
    this.recent.clear();
    this.hand = 0;
    this.history = [];
  }

  resident(): number[] {
    return [...this.table.keys()].sort((a, b) => a - b);
  }

  // Level 4
  walk(address: number, entryBytes: number): number[] {
    const perTable = this.size / entryBytes;
    const [page, offset] = this.split(address);
    return [Math.floor(page / perTable), page % perTable, offset];
  }

  tableBytes(addressBits: number, entryBytes: number): number[] {
    const pages = 2 ** addressBits / this.size;
    const perTable = this.size / entryBytes;
    const directory = (pages / perTable) * entryBytes;
    const tables = new Set([...this.table.keys()].map((page) => Math.floor(page / perTable))).size;
    return [pages * entryBytes, directory + tables * this.size];
  }

  workingSet(window: number): number[] {
    return [...new Set(this.history.slice(-window))].sort((a, b) => a - b);
  }

  thrashing(window: number): boolean {
    return this.frames > 0 && this.workingSet(window).length > this.frames;
  }

  // Translation
  private frameOf(page: number): number | null {
    if (this.tlb !== null) {
      const cached = this.tlb.get(page);
      if (cached !== undefined) {
        this.hits += 1;
        this.tlb.delete(page);
        this.tlb.set(page, cached);
        this.touch(page);
        return cached;
      }
      this.misses += 1;
    }
    let frame = this.table.get(page);
    if (frame === undefined) {
      this.faultCount += 1;
      if (this.frames === 0) return null;
      frame = this.load(page);
    }
    this.touch(page);
    if (this.tlb !== null) {
      if (this.tlb.size === this.tlbEntries) this.tlb.delete(this.tlb.keys().next().value!);
      this.tlb.set(page, frame);
    }
    return frame;
  }

  private touch(page: number): void {
    if (this.frames === 0) return;
    this.recent.delete(page);
    this.recent.add(page);
    this.use[this.table.get(page)!] = true;
  }

  private load(page: number): number {
    let frame: number;
    if (this.table.size < this.frames) {
      frame = this.table.size;
    } else {
      frame = this.victimFrame();
      const victim = this.owner[frame];
      this.table.delete(victim);
      this.loaded.delete(victim);
      this.recent.delete(victim);
      this.tlb?.delete(victim);
    }
    this.table.set(page, frame);
    this.owner[frame] = page;
    this.loaded.add(page);
    return frame;
  }

  private victimFrame(): number {
    if (this.policy === "fifo") return this.table.get(this.loaded.values().next().value!)!;
    if (this.policy === "lru") return this.table.get(this.recent.values().next().value!)!;
    while (this.use[this.hand]) {
      this.use[this.hand] = false;
      this.hand = (this.hand + 1) % this.frames;
    }
    const frame = this.hand;
    this.hand = (this.hand + 1) % this.frames;
    return frame;
  }
}
