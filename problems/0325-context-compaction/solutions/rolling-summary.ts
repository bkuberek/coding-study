const OVERHEAD = 4;
const WORD_PIECE = 4;
const TOKEN_PATTERN = /[A-Za-z0-9]+|[^ \tA-Za-z0-9\n]/g;
const WORD_START = /^[A-Za-z0-9]/;
const NO_LIMIT = -1;
const SYSTEM = "system";
const CALL = "call";
const RESULT = "result";

// A run of letters and digits costs one token for each 4 characters, rounded up; any other
// character that is not white space costs one.
function countTokensOf(text: string): number {
  let total = 0;
  for (const piece of text.match(TOKEN_PATTERN) ?? []) {
    total += WORD_START.test(piece) ? Math.ceil(piece.length / WORD_PIECE) : 1;
  }
  return total;
}

function costOf(content: string): number {
  return countTokensOf(content) + OVERHEAD;
}

interface Turn {
  role: string;
  content: string;
}

interface Item {
  kind: string;
  ref: string;
  content: string;
}

// The tokens of the leading items that two prompts have in common, kind and text alike.
function sharedPrefixCost(old: Item[], current: Item[]): number {
  let shared = 0;
  for (let i = 0; i < Math.min(old.length, current.length); i++) {
    if (old[i].kind !== current[i].kind || old[i].content !== current[i].content) {
      break;
    }
    shared += costOf(current[i].content);
  }
  return shared;
}

interface Summary {
  position: number;
  text: string;
}

interface Layout {
  units: number[];
  summaries: Summary[];
  block: string[];
}

export class ContextWindow {
  private readonly turns: Turn[] = [];
  private readonly units: number[][] = [];
  private liveUnits: number[] = [];
  private readonly answered = new Set<string>();
  private readonly calls = new Set<string>();
  private queue: string[] = [];
  private nextSummary = 0;
  private threshold = NO_LIMIT;
  private keepRecent = 1;
  private lowWater = NO_LIMIT;
  private summaries: Summary[] = [];
  private compactionCount = 0;
  private previous: Item[] = [];
  private readonly reuse: number[] = [];
  private readonly facts = new Map<string, string>();
  private pinBudget = NO_LIMIT;
  private block: string[] = [];
  private readonly compacted: number[] = [];

  // Level 1
  countTokens(text: string): number {
    return countTokensOf(text);
  }

  addTurn(role: string, content: string): number {
    return this.append(role, content);
  }

  window(budget: number, maxTurns: number): number[] {
    const system = this.turns.flatMap((turn, i) => (turn.role === SYSTEM ? [i] : []));
    let remaining = budget - system.reduce((sum, i) => sum + costOf(this.turns[i].content), 0);
    let chosen: number[] = [];
    for (const unit of [...this.units].reverse()) {
      const cost = unit.reduce((sum, i) => sum + costOf(this.turns[i].content), 0);
      if (chosen.length + unit.length > maxTurns || cost > remaining) {
        break;
      }
      chosen = [...unit, ...chosen];
      remaining -= cost;
    }
    return [...system, ...chosen];
  }

  // Level 2
  addCall(callId: string, content: string): number {
    if (this.calls.has(callId)) {
      return -1;
    }
    this.calls.add(callId);
    return this.append(CALL, content);
  }

  addResult(callId: string, content: string): number {
    if (!this.calls.has(callId) || this.answered.has(callId)) {
      return -1;
    }
    this.answered.add(callId);
    return this.append(RESULT, content);
  }

  setSummaries(texts: string[]): void {
    this.queue = [...texts];
    this.nextSummary = 0;
  }

  setCompaction(threshold: number, keepRecent: number): void {
    this.threshold = threshold;
    this.keepRecent = keepRecent;
  }

  context(): string[][] {
    return this.items().map((item) => [item.kind, item.ref, String(costOf(item.content))]);
  }

  compactions(): number {
    return this.compactionCount;
  }

  // Level 3
  setStablePrefix(lowWater: number): void {
    this.lowWater = lowWater;
  }

  prefixReuse(): number[] {
    return [...this.reuse];
  }

  // Level 4
  pinFact(factId: string, text: string): boolean {
    if (this.facts.has(factId)) {
      return false;
    }
    this.facts.set(factId, text);
    this.block = this.blockFor(this.itemsWithoutBlock(this.liveUnits, this.summaries));
    return true;
  }

  setPinBudget(tokens: number): void {
    this.pinBudget = tokens;
  }

  recall(factId: string): boolean {
    const text = this.facts.get(factId);
    return text !== undefined && this.items().some((item) => item.content.includes(text));
  }

  dropped(): string[][] {
    const rows = [...this.compacted].sort((a, b) => a - b).map((i) => ["turn", String(i)]);
    for (const factId of this.facts.keys()) {
      if (!this.recall(factId)) {
        rows.push(["fact", factId]);
      }
    }
    return rows;
  }

  private append(role: string, content: string): number {
    const index = this.turns.length;
    this.turns.push({ role, content });
    if (role !== SYSTEM) {
      const previous = index > 0 ? this.turns[index - 1].role : SYSTEM;
      const joins = (role === CALL || role === RESULT) && (previous === CALL || previous === RESULT);
      if (joins) {
        this.units[this.units.length - 1].push(index);
      } else {
        this.units.push([index]);
        this.liveUnits.push(this.units.length - 1);
      }
    }
    this.compactIfNeeded();
    const prompt = this.items();
    this.reuse.push(sharedPrefixCost(this.previous, prompt));
    this.previous = prompt;
    return index;
  }

  private turnItem(index: number): Item {
    const turn = this.turns[index];
    return { kind: turn.role, ref: String(index), content: turn.content };
  }

  private liveTurns(units: number[]): number[] {
    return units.flatMap((unit) => this.units[unit]);
  }

  private systemItems(): Item[] {
    return this.turns.flatMap((turn, i) => (turn.role === SYSTEM ? [this.turnItem(i)] : []));
  }

  private itemsWithoutBlock(units: number[], summaries: Summary[]): Item[] {
    return [
      ...this.systemItems(),
      ...summaries.map((s) => ({ kind: "summary", ref: String(s.position), content: s.text })),
      ...this.liveTurns(units).map((i) => this.turnItem(i)),
    ];
  }

  private blockFor(others: Item[]): string[] {
    const chosen: string[] = [];
    let used = OVERHEAD;
    for (const [factId, text] of this.facts) {
      if (others.some((item) => item.content.includes(text))) {
        continue;
      }
      const cost = countTokensOf(text);
      if (this.pinBudget !== NO_LIMIT && used + cost > this.pinBudget) {
        continue;
      }
      chosen.push(factId);
      used += cost;
    }
    return chosen;
  }

  private layoutItems(layout: Layout): Item[] {
    const others = this.itemsWithoutBlock(layout.units, layout.summaries);
    if (layout.block.length === 0) {
      return others;
    }
    const head = others.filter((item) => item.kind === SYSTEM || item.kind === "summary");
    const pinned: Item = {
      kind: "pinned",
      ref: layout.block.join(","),
      content: layout.block.map((id) => this.facts.get(id) as string).join("\n"),
    };
    return [...head, pinned, ...others.slice(head.length)];
  }

  private items(): Item[] {
    return this.layoutItems({ units: this.liveUnits, summaries: this.summaries, block: this.block });
  }

  private total(items: Item[]): number {
    return items.reduce((sum, item) => sum + costOf(item.content), 0);
  }

  private compactIfNeeded(): void {
    if (this.threshold === NO_LIMIT || this.total(this.items()) <= this.threshold) {
      return;
    }
    if (this.nextSummary >= this.queue.length) {
      return;
    }
    const candidates = this.liveUnits.slice(0, Math.max(this.liveUnits.length - this.keepRecent, 0));
    if (candidates.length === 0) {
      return;
    }
    const added: Summary = { position: this.nextSummary, text: this.queue[this.nextSummary] };
    const append = this.lowWater !== NO_LIMIT;
    const target = append ? this.lowWater : this.threshold;
    let layout: Layout = { units: this.liveUnits, summaries: this.summaries, block: this.block };
    let count = 0;
    for (count = 1; count <= candidates.length; count++) {
      const units = this.liveUnits.slice(count);
      const summaries = append ? [...this.summaries, added] : [added];
      const block = this.blockFor(this.itemsWithoutBlock(units, summaries));
      layout = { units, summaries, block };
      if (this.total(this.layoutItems(layout)) <= target) {
        break;
      }
    }
    count = Math.min(count, candidates.length);
    this.compacted.push(...this.liveTurns(this.liveUnits.slice(0, count)));
    this.liveUnits = layout.units;
    this.summaries = layout.summaries;
    this.block = layout.block;
    this.nextSummary += 1;
    this.compactionCount += 1;
  }
}
