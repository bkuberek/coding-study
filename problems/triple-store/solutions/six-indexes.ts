// Every triple ever recorded gets a number and a list of spans, the periods during which it was
// present. Six hash indexes list the numbers by subject, predicate, object and the three pairs,
// and one more finds a whole triple, so any pattern with a bound position starts from a short
// list instead of a scan. Removing a triple only closes its span, so the history stays.
//
// A query joins its patterns one at a time, always taking the pattern whose candidate list is
// shortest under the variables bound so far, and a path is a breadth-first walk with a visited
// set, so a cycle ends the walk.
const OPEN = Number.MAX_SAFE_INTEGER;
const CURRENT = OPEN - 1;
const HUGE = 1e15;
const SEP = "\u0000";

interface Span {
  start: number;
  end: number;
  sources: Array<[string, number]>;
}

interface Found {
  row: string[];
  used: number[];
}

interface Match {
  ends: string[];
  id: number;
}

export class TripleStore {
  private triples: Array<[string, string, string]> = [];
  private spans: Span[][] = [];
  private exact = new Map<string, number>();
  private byS = new Map<string, number[]>();
  private byP = new Map<string, number[]>();
  private byO = new Map<string, number[]>();
  private bySP = new Map<string, number[]>();
  private byPO = new Map<string, number[]>();
  private bySO = new Map<string, number[]>();
  private now = 0;
  private live = 0;

  // Level 1
  add(subject: string, predicate: string, obj: string): boolean {
    return this.record(subject, predicate, obj, "", this.now);
  }

  remove(subject: string, predicate: string, obj: string): boolean {
    return this.retract(subject, predicate, obj, this.now);
  }

  size(): number {
    return this.live;
  }

  match(subject: string, predicate: string, obj: string): string[][] {
    const wanted = [subject, predicate, obj].map((term) => (term === "?" ? null : term));
    const found: Array<[string, string, string]> = [];
    const candidates = this.candidates(wanted[0], wanted[1], wanted[2]);
    for (const id of this.each(candidates)) {
      if (this.present(id, CURRENT)) found.push(this.triples[id]);
    }
    found.sort(compareRows);
    return found.map((triple) => [...triple]);
  }

  // Level 2 and 3
  query(patterns: string[][], columns: string[]): string[][] {
    return this.rows(patterns, columns, CURRENT, false)[0];
  }

  // Level 4
  record(subject: string, predicate: string, obj: string, source: string, time: number): boolean {
    this.now = time;
    const key = [subject, predicate, obj].join(SEP);
    let id = this.exact.get(key);
    if (id === undefined) id = this.create(subject, predicate, obj, key);
    const spans = this.spans[id];
    const last = spans[spans.length - 1];
    if (last !== undefined && last.end === OPEN) {
      if (source !== "" && last.sources.every(([known]) => known !== source)) {
        last.sources.push([source, time]);
      }
      return false;
    }
    spans.push({ start: time, end: OPEN, sources: source === "" ? [] : [[source, time]] });
    this.live++;
    return true;
  }

  retract(subject: string, predicate: string, obj: string, time: number): boolean {
    this.now = time;
    const id = this.exact.get([subject, predicate, obj].join(SEP));
    if (id === undefined) return false;
    const spans = this.spans[id];
    const last = spans[spans.length - 1];
    if (last.end !== OPEN) return false;
    last.end = time;
    this.live--;
    return true;
  }

  queryAsOf(patterns: string[][], columns: string[], time: number): string[][] {
    return this.rows(patterns, columns, time, false)[0];
  }

  sourcesAsOf(patterns: string[][], columns: string[], time: number): string[][] {
    return this.rows(patterns, columns, time, true)[1];
  }

  // Storage
  private create(subject: string, predicate: string, obj: string, key: string): number {
    const id = this.triples.length;
    this.triples.push([subject, predicate, obj]);
    this.spans.push([]);
    this.exact.set(key, id);
    push(this.byS, subject, id);
    push(this.byP, predicate, id);
    push(this.byO, obj, id);
    push(this.bySP, subject + SEP + predicate, id);
    push(this.byPO, predicate + SEP + obj, id);
    push(this.bySO, subject + SEP + obj, id);
    return id;
  }

  private spanAt(id: number, when: number): Span | null {
    const spans = this.spans[id];
    for (let at = spans.length - 1; at >= 0; at--) {
      if (spans[at].start <= when) return when < spans[at].end ? spans[at] : null;
    }
    return null;
  }

  private present(id: number, when: number): boolean {
    return this.spanAt(id, when) !== null;
  }

  // The numbers of the triples that can match, from the narrowest index that applies; null means all.
  private candidates(s: string | null, p: string | null, o: string | null): number[] | null {
    if (s !== null && p !== null && o !== null) {
      const id = this.exact.get([s, p, o].join(SEP));
      return id === undefined ? [] : [id];
    }
    const none: number[] = [];
    if (s !== null && p !== null) return this.bySP.get(s + SEP + p) ?? none;
    if (p !== null && o !== null) return this.byPO.get(p + SEP + o) ?? none;
    if (s !== null && o !== null) return this.bySO.get(s + SEP + o) ?? none;
    if (s !== null) return this.byS.get(s) ?? none;
    if (p !== null) return this.byP.get(p) ?? none;
    if (o !== null) return this.byO.get(o) ?? none;
    return null;
  }

  private count(candidates: number[] | null): number {
    return candidates === null ? this.triples.length : candidates.length;
  }

  private each(candidates: number[] | null): number[] {
    if (candidates !== null) return candidates;
    return this.triples.map((_, id) => id);
  }

  // Queries
  private rows(patterns: string[][], columns: string[], when: number, track: boolean): [string[][], string[][]] {
    const found: Found[] = [];
    this.search(patterns, new Map(), [], columns, when, track, found);
    const distinct = new Map<string, string[]>();
    for (const { row } of found) distinct.set(row.join(SEP), row);
    const rows = [...distinct.values()].sort(compareRows);
    if (!track) return [rows, []];
    const sources = new Map<string, Set<string>>();
    for (const row of rows) sources.set(row.join(SEP), new Set());
    for (const { row, used } of found) {
      const names = sources.get(row.join(SEP))!;
      for (const id of used) {
        const span = this.spanAt(id, when);
        if (span === null) continue;
        for (const [name, at] of span.sources) if (at <= when) names.add(name);
      }
    }
    return [rows, rows.map((row) => [...sources.get(row.join(SEP))!].sort())];
  }

  private search(
    remaining: string[][],
    bindings: Map<string, string>,
    used: number[],
    columns: string[],
    when: number,
    track: boolean,
    found: Found[],
  ): void {
    if (remaining.length === 0) {
      found.push({ row: columns.map((name) => bindings.get(name)!), used: track ? [...used] : [] });
      return;
    }
    let best = 0;
    let bestCost = Infinity;
    remaining.forEach((pattern, at) => {
      const cost = this.cost(pattern, bindings);
      if (cost < bestCost) {
        bestCost = cost;
        best = at;
      }
    });
    const pattern = remaining[best];
    const rest = remaining.filter((_, at) => at !== best);
    for (const { ends, id } of this.matches(pattern, bindings, when)) {
      const undo: string[] = [];
      if (this.unify(pattern, ends, bindings, undo)) {
        if (id >= 0) used.push(id);
        this.search(rest, bindings, used, columns, when, track, found);
        if (id >= 0) used.pop();
      }
      for (const name of undo) bindings.delete(name);
    }
  }

  private value(token: string, bindings: Map<string, string>): string | null {
    if (token === "?") return null;
    if (token.startsWith("?")) return bindings.get(token) ?? null;
    return token;
  }

  private unify(pattern: string[], ends: string[], bindings: Map<string, string>, undo: string[]): boolean {
    const tokens = ends.length === 3 ? pattern : [pattern[0], pattern[2]];
    for (let at = 0; at < tokens.length; at++) {
      const token = tokens[at];
      if (token === "?") continue;
      if (!token.startsWith("?")) {
        if (token !== ends[at]) return false;
      } else if (bindings.has(token)) {
        if (bindings.get(token) !== ends[at]) return false;
      } else {
        bindings.set(token, ends[at]);
        undo.push(token);
      }
    }
    return true;
  }

  private cost(pattern: string[], bindings: Map<string, string>): number {
    const s = this.value(pattern[0], bindings);
    const p = this.value(pattern[1], bindings);
    const o = this.value(pattern[2], bindings);
    if (pattern[1].endsWith("+")) {
      if (s === null && o === null) return HUGE;
      return (this.byP.get(pattern[1].slice(0, -1)) ?? []).length;
    }
    return this.count(this.candidates(s, p, o));
  }

  private matches(pattern: string[], bindings: Map<string, string>, when: number): Match[] {
    const s = this.value(pattern[0], bindings);
    const p = this.value(pattern[1], bindings);
    const o = this.value(pattern[2], bindings);
    if (pattern[1].endsWith("+")) {
      return this.pathPairs(s, pattern[1].slice(0, -1), o, when).map((pair) => ({ ends: pair, id: -1 }));
    }
    const found: Match[] = [];
    for (const id of this.each(this.candidates(s, p, o))) {
      if (this.present(id, when)) found.push({ ends: this.triples[id], id });
    }
    return found;
  }

  private pathPairs(s: string | null, p: string, o: string | null, when: number): string[][] {
    if (s !== null) {
      const reached = this.reach(s, p, true, when);
      if (o !== null) return reached.has(o) ? [[s, o]] : [];
      return [...reached].map((node) => [s, node]);
    }
    if (o !== null) return [...this.reach(o, p, false, when)].map((node) => [node, o]);
    const starts = new Set<string>();
    for (const id of this.byP.get(p) ?? []) {
      if (this.present(id, when)) starts.add(this.triples[id][0]);
    }
    const pairs: string[][] = [];
    for (const start of starts) {
      for (const node of this.reach(start, p, true, when)) pairs.push([start, node]);
    }
    return pairs;
  }

  // The nodes at the end of one or more hops; the start is in it only through a cycle.
  private reach(start: string, p: string, forward: boolean, when: number): Set<string> {
    const seen = new Set<string>();
    const queue = [start];
    for (let next = 0; next < queue.length; next++) {
      const node = queue[next];
      const ids = forward ? this.bySP.get(node + SEP + p) : this.byPO.get(p + SEP + node);
      for (const id of ids ?? []) {
        if (!this.present(id, when)) continue;
        const following = forward ? this.triples[id][2] : this.triples[id][0];
        if (!seen.has(following)) {
          seen.add(following);
          queue.push(following);
        }
      }
    }
    return seen;
  }
}

function push(index: Map<string, number[]>, key: string, id: number): void {
  const list = index.get(key);
  if (list === undefined) index.set(key, [id]);
  else list.push(id);
}

function compareRows(a: readonly string[], b: readonly string[]): number {
  for (let at = 0; at < a.length; at++) {
    if (a[at] < b[at]) return -1;
    if (a[at] > b[at]) return 1;
  }
  return 0;
}
