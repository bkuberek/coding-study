const OVER_BUDGET = "OVER_BUDGET";
// Two items are near-duplicates when shared / union > 4 / 5, compared in integers.
const SIMILARITY_NUMERATOR = 4;
const SIMILARITY_DENOMINATOR = 5;

class Item {
  readonly id: string;
  readonly words: ReadonlySet<string>;
  readonly tokens: number;
  readonly score: number;
  pinned = false;
  category: string | null = null;

  constructor(id: string, text: string, tokens: number, score: number) {
    this.id = id;
    this.words = new Set(text.split(" "));
    this.tokens = tokens;
    this.score = score;
  }

  duplicates(other: Item): boolean {
    let shared = 0;
    for (const word of this.words) {
      if (other.words.has(word)) {
        shared += 1;
      }
    }
    const union = this.words.size + other.words.size - shared;
    return shared * SIMILARITY_DENOMINATOR > union * SIMILARITY_NUMERATOR;
  }
}

// Pinned items first, then higher score, then fewer tokens, then smaller id in plain string order.
function packingOrder(a: Item, b: Item): number {
  if (a.pinned !== b.pinned) {
    return a.pinned ? -1 : 1;
  }
  return b.score - a.score || a.tokens - b.tokens || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
}

export class ContextPacker {
  private readonly items = new Map<string, Item>();
  private readonly caps = new Map<string, number>();

  // Level 1
  addItem(timestamp: number, itemId: string, text: string, tokens: number, score: number): boolean {
    if (this.items.has(itemId)) {
      return false;
    }
    this.items.set(itemId, new Item(itemId, text, tokens, score));
    return true;
  }

  removeItem(timestamp: number, itemId: string): boolean {
    return this.items.delete(itemId);
  }

  pack(timestamp: number, budget: number): string[] {
    const { survivors } = this.collapse();
    const pinnedTokens = survivors
      .filter((item) => item.pinned)
      .reduce((total, item) => total + item.tokens, 0);
    if (pinnedTokens > budget) {
      return [OVER_BUDGET];
    }
    let remaining = budget;
    const taken = new Map<string, number>();
    const chosen: string[] = [];
    for (const item of survivors) {
      if (!item.pinned && (item.tokens > remaining || this.isFull(item, taken))) {
        continue;
      }
      chosen.push(item.id);
      remaining -= item.tokens;
      if (item.category !== null) {
        taken.set(item.category, (taken.get(item.category) ?? 0) + 1);
      }
    }
    return chosen;
  }

  // Level 2
  pin(timestamp: number, itemId: string): boolean {
    const item = this.items.get(itemId);
    if (item === undefined || item.pinned) {
      return false;
    }
    item.pinned = true;
    return true;
  }

  unpin(timestamp: number, itemId: string): boolean {
    const item = this.items.get(itemId);
    if (item === undefined || !item.pinned) {
      return false;
    }
    item.pinned = false;
    return true;
  }

  // Level 3
  setCategory(timestamp: number, itemId: string, category: string): boolean {
    const item = this.items.get(itemId);
    if (item === undefined) {
      return false;
    }
    item.category = category;
    return true;
  }

  setCap(timestamp: number, category: string, cap: number): void {
    this.caps.set(category, cap);
  }

  // Level 4
  duplicateOf(timestamp: number, itemId: string): string {
    return this.collapse().knockedOut.get(itemId) ?? "";
  }

  private isFull(item: Item, taken: ReadonlyMap<string, number>): boolean {
    if (item.category === null) {
      return false;
    }
    const cap = this.caps.get(item.category);
    return cap !== undefined && (taken.get(item.category) ?? 0) >= cap;
  }

  // The items that survive, in packing order, and which kept item knocked out each other one.
  // An unpinned item is knocked out by the first item kept before it that it near-duplicates.
  private collapse(): { survivors: Item[]; knockedOut: Map<string, string> } {
    const survivors: Item[] = [];
    const knockedOut = new Map<string, string>();
    for (const item of [...this.items.values()].sort(packingOrder)) {
      const keeper = item.pinned ? undefined : survivors.find((kept) => item.duplicates(kept));
      if (keeper === undefined) {
        survivors.push(item);
      } else {
        knockedOut.set(item.id, keeper.id);
      }
    }
    return { survivors, knockedOut };
  }
}
