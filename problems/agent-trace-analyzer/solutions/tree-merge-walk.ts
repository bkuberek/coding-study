const NANOS_PER_MICRO = 1000;

class Span {
  readonly id: string;
  readonly parent: string;
  readonly kind: string;
  readonly name: string;
  readonly start: number;
  readonly end: number;
  readonly late: boolean;
  readonly status: string;
  readonly attributes = new Map<string, string>();

  constructor(fields: [string, string, string, string, number, number, string], attributes: string[]) {
    const [id, parent, kind, name, start, end, status] = fields;
    this.id = id;
    this.parent = parent;
    this.kind = kind;
    this.name = name;
    this.start = start;
    this.late = end < start;
    this.end = Math.max(start, end);
    this.status = status;
    for (const attribute of attributes) {
      const at = attribute.indexOf("=");
      const key = at < 0 ? attribute : attribute.slice(0, at);
      if (!this.attributes.has(key)) {
        this.attributes.set(key, at < 0 ? "" : attribute.slice(at + 1));
      }
    }
  }

  total(): number {
    return this.end - this.start;
  }

  tokensIn(): number {
    return Number(this.attributes.get("input_tokens") ?? "0");
  }

  tokensOut(): number {
    return Number(this.attributes.get("output_tokens") ?? "0");
  }
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function byStartThenId(a: Span, b: Span): number {
  return a.start - b.start || compareText(a.id, b.id);
}

/** The spans reachable from a root, with their depths, children by (start, id), roots under "". */
class Tree {
  readonly children = new Map<string, Span[]>();
  readonly preorder: { depth: number; span: Span }[] = [];
  readonly depth = new Map<string, number>();

  constructor(spans: Map<string, Span>) {
    for (const span of spans.values()) {
      const parent = spans.has(span.parent) ? span.parent : "";
      this.childrenOf(parent).push(span);
    }
    for (const listed of this.children.values()) {
      listed.sort(byStartThenId);
    }
    const stack = this.childrenOf("")
      .slice()
      .reverse()
      .map((span) => ({ depth: 1, span }));
    while (stack.length > 0) {
      const entry = stack.pop()!;
      this.preorder.push(entry);
      this.depth.set(entry.span.id, entry.depth);
      const below = this.childrenOf(entry.span.id);
      for (let i = below.length - 1; i >= 0; i--) {
        stack.push({ depth: entry.depth + 1, span: below[i] });
      }
    }
  }

  childrenOf(id: string): Span[] {
    let listed = this.children.get(id);
    if (listed === undefined) {
      listed = [];
      this.children.set(id, listed);
    }
    return listed;
  }

  spans(): Span[] {
    return this.preorder.map((entry) => entry.span);
  }

  subtree(span: Span): Span[] {
    const found: Span[] = [];
    const stack = [span];
    while (stack.length > 0) {
      const current = stack.pop()!;
      found.push(current);
      stack.push(...this.childrenOf(current.id));
    }
    return found;
  }
}

/** Nanos (thousandths of a micro) to whole micros, halves up. */
function rounded(nanos: number): number {
  return Math.floor((nanos + NANOS_PER_MICRO / 2) / NANOS_PER_MICRO);
}

function trimSpaces(text: string): string {
  let low = 0;
  let high = text.length;
  while (low < high && text[low] === " ") low++;
  while (high > low && text[high - 1] === " ") high--;
  return text.slice(low, high);
}

function normalizedArgs(text: string): string {
  const pairs: [string, string][] = [];
  for (const raw of text.split("&")) {
    const piece = trimSpaces(raw);
    if (piece === "") {
      continue;
    }
    const at = piece.indexOf("=");
    const name = at < 0 ? piece : piece.slice(0, at);
    const value = at < 0 ? "" : piece.slice(at + 1);
    pairs.push([trimSpaces(name).toLowerCase(), trimSpaces(value)]);
  }
  pairs.sort((a, b) => compareText(a[0], b[0]) || compareText(a[1], b[1]));
  return pairs.map(([name, value]) => `${name}=${value}`).join("&");
}

export class TraceAnalyzer {
  private readonly events: { id: string; fresh: boolean }[] = [];
  private readonly spanById = new Map<string, Span>();
  private readonly prices = new Map<string, [number, number]>();
  private cached: Tree | null = null;

  // Level 1
  addSpan(
    spanId: string,
    parentId: string,
    kind: string,
    name: string,
    start: number,
    end: number,
    status: string,
    attributes: string[],
  ): boolean {
    const fresh = !this.spanById.has(spanId);
    this.events.push({ id: spanId, fresh });
    if (fresh) {
      this.spanById.set(spanId, new Span([spanId, parentId, kind, name, start, end, status], attributes));
      this.cached = null;
    }
    return fresh;
  }

  errors(): string[][] {
    const tree = this.tree();
    const rows: string[][] = [];
    this.events.forEach((event, position) => {
      const codes: string[] = [];
      if (!event.fresh) {
        codes.push("duplicate_id");
      } else {
        const span = this.spanById.get(event.id)!;
        if (span.late) codes.push("end_before_start");
        if (span.parent !== "" && !this.spanById.has(span.parent)) codes.push("unknown_parent");
        if (!tree.depth.has(span.id)) codes.push("parent_cycle");
      }
      for (const code of codes) {
        rows.push([String(position), code, event.id]);
      }
    });
    return rows;
  }

  outline(): string[][] {
    return this.tree().preorder.map(({ depth, span }) => [String(depth), span.id, span.kind, span.name]);
  }

  depth(): number {
    let deepest = 0;
    for (const depth of this.tree().depth.values()) {
      deepest = Math.max(deepest, depth);
    }
    return deepest;
  }

  kindCounts(): string[][] {
    const counts = new Map<string, number>();
    for (const span of this.tree().spans()) {
      counts.set(span.kind, (counts.get(span.kind) ?? 0) + 1);
    }
    return [...counts.keys()].sort(compareText).map((kind) => [kind, String(counts.get(kind))]);
  }

  // Level 2
  timing(spanId: string): number[] {
    const span = this.treeSpan(spanId);
    return span === undefined ? [] : [span.total(), this.selfTime(span)];
  }

  criticalPath(): string[] {
    return this.critical().map((span) => span.id);
  }

  slowest(n: number): string[][] {
    const rows = this.tree()
      .spans()
      .map((span) => ({ id: span.id, own: this.selfTime(span), total: span.total() }));
    rows.sort((a, b) => b.own - a.own || b.total - a.total || compareText(a.id, b.id));
    return rows.slice(0, n).map((row) => [row.id, String(row.own), String(row.total)]);
  }

  // Level 3
  setPrice(model: string, inputPrice: number, outputPrice: number): boolean {
    const fresh = !this.prices.has(model);
    this.prices.set(model, [inputPrice, outputPrice]);
    return fresh;
  }

  rollup(spanId: string): number[] {
    const span = this.treeSpan(spanId);
    if (span === undefined) {
      return [];
    }
    let treeIn = 0;
    let treeOut = 0;
    let treeNanos = 0;
    for (const member of this.tree().subtree(span)) {
      treeIn += member.tokensIn();
      treeOut += member.tokensOut();
      treeNanos += this.nanos(member);
    }
    return [span.tokensIn(), span.tokensOut(), rounded(this.nanos(span)), treeIn, treeOut, rounded(treeNanos)];
  }

  costByKind(): string[][] {
    const totals = new Map<string, { tokensIn: number; tokensOut: number; nanos: number }>();
    for (const span of this.tree().spans()) {
      const entry = totals.get(span.kind) ?? { tokensIn: 0, tokensOut: 0, nanos: 0 };
      entry.tokensIn += span.tokensIn();
      entry.tokensOut += span.tokensOut();
      entry.nanos += this.nanos(span);
      totals.set(span.kind, entry);
    }
    return [...totals]
      .sort(([kindA, a], [kindB, b]) => b.nanos - a.nanos || compareText(kindA, kindB))
      .map(([kind, entry]) => [kind, String(entry.tokensIn), String(entry.tokensOut), String(rounded(entry.nanos))]);
  }

  unpriced(): string[] {
    return this.tree()
      .spans()
      .filter((span) => this.isUnpriced(span))
      .map((span) => span.id)
      .sort(compareText);
  }

  // Level 4
  retryLoops(minRun: number): string[][] {
    const tree = this.tree();
    const loops: Span[][] = [];
    for (const siblings of tree.children.values()) {
      let run: Span[] = [];
      for (const span of siblings) {
        if (span.kind !== "tool" || !tree.depth.has(span.id)) {
          continue;
        }
        if (run.length > 0 && span.status === "error" && this.call(span) === this.call(run[0])) {
          run.push(span);
          continue;
        }
        if (run.length >= minRun) {
          loops.push(run);
        }
        run = span.status === "error" ? [span] : [];
      }
      if (run.length >= minRun) {
        loops.push(run);
      }
    }
    loops.sort((a, b) => byStartThenId(a[0], b[0]));
    return loops.map((run) => [
      run[0].id,
      run[run.length - 1].id,
      run[0].name,
      normalizedArgs(run[0].attributes.get("args") ?? ""),
      String(run.length),
    ]);
  }

  rootCause(): string[] {
    const cause = this.cause();
    return cause === undefined ? [] : [cause.id, cause.kind, cause.name];
  }

  report(minRun: number): string[] {
    const spans = this.tree().spans();
    const critical = this.critical();
    const cause = this.cause();
    const loops = this.retryLoops(minRun);
    const malformed = new Set(this.errors().map((row) => row[0])).size;
    const status = critical.length === 0 ? "empty" : critical[0].status === "error" ? "failed" : "ok";
    let tokens = 0;
    let nanos = 0;
    for (const span of spans) {
      tokens += span.tokensIn() + span.tokensOut();
      nanos += this.nanos(span);
    }
    const repeated = loops.reduce((sum, loop) => sum + Number(loop[4]) - 1, 0);
    return [
      `spans: ${spans.length}`,
      `depth: ${this.depth()}`,
      `malformed: ${malformed}`,
      `status: ${status}`,
      `critical path: ${critical.length}`,
      `duration: ${critical.length > 0 ? critical[0].total() : 0}`,
      `root cause: ${cause === undefined ? "none" : cause.id}`,
      `retry loops: ${loops.length}`,
      `repeated calls: ${repeated}`,
      `tokens: ${tokens}`,
      `cost: ${rounded(nanos)}`,
      `unpriced: ${this.unpriced().length}`,
    ];
  }

  // Helpers
  private tree(): Tree {
    if (this.cached === null) {
      this.cached = new Tree(this.spanById);
    }
    return this.cached;
  }

  private treeSpan(spanId: string): Span | undefined {
    return this.tree().depth.has(spanId) ? this.spanById.get(spanId) : undefined;
  }

  /** The span's length minus the union of its children, each clipped to the span. */
  private selfTime(span: Span): number {
    const clipped = this.tree()
      .childrenOf(span.id)
      .map((child): [number, number] => [Math.max(child.start, span.start), Math.min(child.end, span.end)])
      .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    let covered = 0;
    let reach = span.start;
    for (const [from, to] of clipped) {
      const low = Math.max(from, reach);
      if (to > low) {
        covered += to - low;
        reach = to;
      }
    }
    return span.total() - covered;
  }

  private critical(): Span[] {
    const tree = this.tree();
    const roots = tree.childrenOf("");
    if (roots.length === 0) {
      return [];
    }
    const latestFirst = (a: Span, b: Span) => b.end - a.end || a.start - b.start || compareText(a.id, b.id);
    const path: Span[] = [];
    const pending = [roots.slice().sort(latestFirst)[0]];
    while (pending.length > 0) {
      const span = pending.pop()!;
      path.push(span);
      // The cursor only moves back, so a child that ends after it now never fits later:
      // one scan of the children, latest end first, finds every pick in turn.
      let cursor = span.end;
      const chosen: Span[] = [];
      for (const child of tree.childrenOf(span.id).slice().sort(latestFirst)) {
        if (child.end <= cursor) {
          chosen.push(child);
          cursor = child.start;
        }
      }
      pending.push(...chosen);
    }
    return path;
  }

  private cause(): Span | undefined {
    const critical = this.critical();
    if (critical.length === 0 || critical[0].status !== "error") {
      return undefined;
    }
    const depth = this.tree().depth;
    const failing = critical.filter((span) => span.status === "error");
    failing.sort((a, b) => a.end - b.end || depth.get(b.id)! - depth.get(a.id)! || compareText(a.id, b.id));
    return failing[0];
  }

  private isUnpriced(span: Span): boolean {
    const model = span.attributes.get("model");
    return span.tokensIn() + span.tokensOut() > 0 && (model === undefined || !this.prices.has(model));
  }

  private nanos(span: Span): number {
    if (span.tokensIn() + span.tokensOut() === 0 || this.isUnpriced(span)) {
      return 0;
    }
    const [priceIn, priceOut] = this.prices.get(span.attributes.get("model")!)!;
    return span.tokensIn() * priceIn + span.tokensOut() * priceOut;
  }

  private call(span: Span): string {
    return `${span.name}&&${normalizedArgs(span.attributes.get("args") ?? "")}`;
  }
}
