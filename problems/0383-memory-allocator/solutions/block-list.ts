// The heap is a list of blocks in address order, each with its start, its size (header included)
// and whether it is in use. Allocating splits a free block; freeing marks it free and, with
// coalescing or in the buddy system, merges it with its free neighbors. Next fit keeps a rover:
// the address where its next search starts.

const HEADER = 8;
const ALIGN = 8;
const MIN_BLOCK = 16;
const POLICIES = ["first-fit", "next-fit", "best-fit"];

type Block = { start: number; size: number; used: boolean; requested: number };

export class MemoryAllocator {
  private heapSize: number;
  private blocks: Block[];
  private coalescing = false;
  private policy = "first-fit";
  private started = false;
  private rover = 0;

  constructor(heapSize: number) {
    this.heapSize = heapSize;
    this.blocks = [{ start: 0, size: heapSize, used: false, requested: 0 }];
  }

  // --- helpers
  private position(start: number): number {
    return this.blocks.findIndex((block) => block.start === start);
  }

  private blockSize(size: number): number {
    if (this.policy === "buddy") {
      let block = MIN_BLOCK;
      while (block < size + HEADER) block *= 2;
      return block;
    }
    return HEADER + Math.ceil(size / ALIGN) * ALIGN;
  }

  // The position of the free block the policy picks, or -1.
  private choose(need: number): number {
    const fits: number[] = [];
    this.blocks.forEach((block, i) => {
      if (!block.used && block.size >= need) fits.push(i);
    });
    if (fits.length === 0) return -1;
    if (this.policy === "next-fit") {
      const here = this.position(this.rover);
      return fits.find((i) => i >= here) ?? fits[0];
    }
    if (this.policy === "best-fit" || this.policy === "buddy") {
      let best = fits[0];
      for (const i of fits) if (this.blocks[i].size < this.blocks[best].size) best = i;
      return best;
    }
    return fits[0];
  }

  private split(position: number, keep: number): void {
    const block = this.blocks[position];
    const rest = { start: block.start + keep, size: block.size - keep, used: false, requested: 0 };
    block.size = keep;
    this.blocks.splice(position + 1, 0, rest);
  }

  private mergeWithNext(position: number): void {
    const block = this.blocks[position];
    const following = this.blocks.splice(position + 1, 1)[0];
    block.size += following.size;
    if (this.rover === following.start) this.rover = block.start;
  }

  private freeBuddies(position: number): void {
    while (this.blocks[position].size < this.heapSize) {
      const block = this.blocks[position];
      const other = this.position(block.start ^ block.size);
      if (other < 0 || this.blocks[other].used || this.blocks[other].size !== block.size) return;
      position = Math.min(position, other);
      this.mergeWithNext(position);
    }
  }

  // Level 1
  allocate(size: number): number {
    this.started = true;
    const need = this.blockSize(size);
    const position = this.choose(need);
    if (position < 0) return -1;
    if (this.policy === "buddy") {
      while (this.blocks[position].size > need) this.split(position, this.blocks[position].size / 2);
    } else if (this.blocks[position].size - need >= MIN_BLOCK) {
      this.split(position, need);
    }
    const block = this.blocks[position];
    block.used = true;
    block.requested = size;
    this.rover = (block.start + block.size) % this.heapSize;
    return block.start + HEADER;
  }

  free(address: number): string {
    const position = this.position(address - HEADER);
    if (position < 0 || !this.blocks[position].used) return "invalid";
    this.blocks[position].used = false;
    if (this.policy === "buddy") {
      this.freeBuddies(position);
    } else if (this.coalescing) {
      if (position + 1 < this.blocks.length && !this.blocks[position + 1].used) this.mergeWithNext(position);
      if (position > 0 && !this.blocks[position - 1].used) this.mergeWithNext(position - 1);
    }
    return "ok";
  }

  heapMap(): string[] {
    return this.blocks.map((b) => `${b.start} ${b.size} ${b.used ? "used" : "free"}`);
  }

  // Level 2
  setCoalescing(enabled: boolean): string {
    if (this.started) return "too-late";
    this.coalescing = enabled;
    return "ok";
  }

  freeReport(): number[] {
    const sizes = this.blocks.filter((b) => !b.used).map((b) => b.size);
    const total = sizes.reduce((sum, size) => sum + size, 0);
    const largest = sizes.reduce((most, size) => Math.max(most, size), 0);
    const fragmentation = total === 0 ? 0 : Math.floor((100 * (total - largest)) / total);
    return [sizes.length, total, largest, fragmentation];
  }

  // Level 3
  setPolicy(policy: string): string {
    if (!POLICIES.includes(policy) && policy !== "buddy") return "unknown-policy";
    if (this.started) return "too-late";
    if (policy === "buddy" && (this.heapSize & (this.heapSize - 1)) !== 0) return "bad-size";
    this.policy = policy;
    return "ok";
  }

  compare(trace: number[]): number[][] {
    return POLICIES.map((policy) => {
      const heap = new MemoryAllocator(this.heapSize);
      heap.setCoalescing(this.coalescing);
      heap.setPolicy(policy);
      const addresses: number[] = [];
      let failed = 0;
      for (const step of trace) {
        if (step > 0) {
          addresses.push(heap.allocate(step));
          if (addresses[addresses.length - 1] < 0) failed++;
        } else if (addresses[-step - 1] >= 0) {
          heap.free(addresses[-step - 1]);
        }
      }
      return [failed, ...heap.freeReport()];
    });
  }

  // Level 4
  wasted(): number {
    return this.blocks
      .filter((b) => b.used)
      .reduce((sum, b) => sum + b.size - HEADER - b.requested, 0);
  }
}
