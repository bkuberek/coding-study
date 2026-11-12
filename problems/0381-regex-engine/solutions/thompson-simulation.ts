// A recursive-descent parser builds the syntax tree; Thompson's construction turns it into an
// automaton with one state per character, class or operator; matching runs every live state in
// step with the text, so it never backtracks. Compiled automata are cached by pattern.

type Range = [string, string];

type Node =
  | { kind: "lit"; char: string }
  | { kind: "any" }
  | { kind: "empty" }
  | { kind: "class"; negated: boolean; items: Range[] }
  | { kind: "cat" | "alt"; parts: Node[] }
  | { kind: "star" | "plus" | "opt"; inner: Node };

class PatternError extends Error {
  code: string;
  position: number;

  constructor(code: string, position: number) {
    super(code);
    this.code = code;
    this.position = position;
  }
}

const REPEATS = new Map<string, "star" | "plus" | "opt">([
  ["*", "star"],
  ["+", "plus"],
  ["?", "opt"],
]);

// Recursive descent; a pattern has at most 100 characters, so the recursion stays shallow.
class Parser {
  private text: string;
  private pos = 0;

  constructor(pattern: string) {
    this.text = pattern;
  }

  private peek(): string {
    return this.pos < this.text.length ? this.text[this.pos] : "";
  }

  parse(): Node {
    const node = this.alternation();
    if (this.pos < this.text.length) throw new PatternError("unmatched-paren", this.pos);
    return node;
  }

  private alternation(): Node {
    const branches = [this.sequence()];
    while (this.peek() === "|") {
      this.pos++;
      branches.push(this.sequence());
    }
    return branches.length === 1 ? branches[0] : { kind: "alt", parts: branches };
  }

  private sequence(): Node {
    const items: Node[] = [];
    while (this.peek() !== "" && this.peek() !== "|" && this.peek() !== ")") {
      items.push(this.repetition());
    }
    if (items.length === 0) return { kind: "empty" };
    return items.length === 1 ? items[0] : { kind: "cat", parts: items };
  }

  private repetition(): Node {
    if (REPEATS.has(this.peek())) throw new PatternError("nothing-to-repeat", this.pos);
    let node = this.atom();
    while (REPEATS.has(this.peek())) {
      node = { kind: REPEATS.get(this.peek())!, inner: node };
      this.pos++;
    }
    return node;
  }

  private atom(): Node {
    const start = this.pos;
    const char = this.peek();
    this.pos++;
    if (char === "(") {
      const inner = this.alternation();
      if (this.peek() !== ")") throw new PatternError("unclosed-group", start);
      this.pos++;
      return inner;
    }
    if (char === ".") return { kind: "any" };
    if (char === "[") return this.charClass(start);
    return { kind: "lit", char };
  }

  private charClass(start: number): Node {
    const negated = this.peek() === "^";
    if (negated) this.pos++;
    const items: Range[] = [];
    for (;;) {
      if (this.pos >= this.text.length) throw new PatternError("unclosed-class", start);
      if (this.peek() === "]") {
        if (items.length === 0) throw new PatternError("empty-class", start);
        this.pos++;
        return { kind: "class", negated, items };
      }
      const lowAt = this.pos;
      const low = this.text[lowAt];
      this.pos++;
      const isRange =
        this.peek() === "-" && this.pos + 1 < this.text.length && this.text[this.pos + 1] !== "]";
      if (isRange) {
        const high = this.text[this.pos + 1];
        if (high < low) throw new PatternError("bad-range", lowAt);
        this.pos += 2;
        items.push([low, high]);
      } else {
        items.push([low, low]);
      }
    }
  }
}

function showClass(negated: boolean, items: Range[]): string {
  const parts = items.map(([low, high]) => (low === high ? `'${low}'` : `'${low}'-'${high}'`));
  return (negated ? "notclass(" : "class(") + parts.join(",") + ")";
}

function show(node: Node): string {
  switch (node.kind) {
    case "lit":
      return `'${node.char}'`;
    case "any":
    case "empty":
      return node.kind;
    case "class":
      return showClass(node.negated, node.items);
    case "cat":
    case "alt":
      return `${node.kind}(${node.parts.map(show).join(",")})`;
    default:
      return `${node.kind}(${show(node.inner)})`;
  }
}

type Hole = [number, number];

// The automaton: parallel arrays of kind, the node that labels a char or class state, and arrows.
class Automaton {
  kind: string[] = [];
  label: (Node | null)[] = [];
  outs: number[][] = [];
  final = 0;

  constructor(root: Node) {
    const start = this.fragment(root);
    const match = this.add("match", null, 0);
    this.patch(start.holes, match);
    this.renumber(start.state);
  }

  private add(kind: string, label: Node | null, arrows: number): number {
    this.kind.push(kind);
    this.label.push(label);
    this.outs.push(new Array<number>(arrows).fill(-1));
    return this.kind.length - 1;
  }

  private patch(holes: Hole[], target: number): void {
    for (const [state, index] of holes) this.outs[state][index] = target;
  }

  private fragment(node: Node): { state: number; holes: Hole[] } {
    switch (node.kind) {
      case "lit":
      case "any":
      case "empty":
      case "class": {
        const state = this.add(node.kind === "lit" ? "char" : node.kind, node, 1);
        return { state, holes: [[state, 0]] };
      }
      case "cat": {
        const first = this.fragment(node.parts[0]);
        let holes = first.holes;
        for (const part of node.parts.slice(1)) {
          const next = this.fragment(part);
          this.patch(holes, next.state);
          holes = next.holes;
        }
        return { state: first.state, holes };
      }
      case "alt": {
        const split = this.add("split", null, node.parts.length);
        const holes: Hole[] = [];
        node.parts.forEach((part, index) => {
          const side = this.fragment(part);
          this.outs[split][index] = side.state;
          holes.push(...side.holes);
        });
        return { state: split, holes };
      }
      default: {
        const inner = this.fragment(node.inner);
        const split = this.add("split", null, 2);
        this.outs[split][0] = inner.state;
        if (node.kind === "star") {
          this.patch(inner.holes, split);
          return { state: split, holes: [[split, 1]] };
        }
        if (node.kind === "plus") {
          this.patch(inner.holes, split);
          return { state: inner.state, holes: [[split, 1]] };
        }
        return { state: split, holes: [...inner.holes, [split, 1]] };
      }
    }
  }

  // Breadth first from the start state: the start is 0, and each arrow's unseen target is next.
  private renumber(start: number): void {
    const number = new Map<number, number>([[start, 0]]);
    const order = [start];
    for (let i = 0; i < order.length; i++) {
      for (const target of this.outs[order[i]]) {
        if (!number.has(target)) {
          number.set(target, order.length);
          order.push(target);
        }
      }
    }
    this.label = order.map((state) => this.label[state]);
    this.outs = order.map((state) => this.outs[state].map((target) => number.get(target)!));
    this.kind = order.map((state) => this.kind[state]);
    this.final = this.kind.indexOf("match");
  }

  line(state: number): string {
    const kind = this.kind[state];
    const label = this.label[state];
    let head = `${state}: `;
    if (label !== null && label.kind === "lit") head += `char '${label.char}'`;
    else if (label !== null && label.kind === "class") head += showClass(label.negated, label.items);
    else head += kind;
    const outs = this.outs[state];
    return outs.length === 0 ? head : `${head} -> ${outs.join(", ")}`;
  }

  accepts(state: number, char: string): boolean {
    const label = this.label[state];
    if (this.kind[state] === "any") return true;
    if (label === null) return false;
    if (label.kind === "lit") return label.char === char;
    if (label.kind === "class") {
      const inside = label.items.some(([low, high]) => low <= char && char <= high);
      return inside !== label.negated;
    }
    return false;
  }

  // Every state reachable from the sources through split and empty arrows, sources included.
  closure(sources: number[]): number[] {
    const seen = new Set<number>();
    const reached: number[] = [];
    const stack = [...sources].reverse();
    while (stack.length > 0) {
      const state = stack.pop()!;
      if (seen.has(state)) continue;
      seen.add(state);
      reached.push(state);
      if (this.kind[state] === "split" || this.kind[state] === "empty") {
        for (let i = this.outs[state].length - 1; i >= 0; i--) stack.push(this.outs[state][i]);
      }
    }
    return reached;
  }

  private advance(current: number[], char: string): number[] {
    return this.closure(current.filter((s) => this.accepts(s, char)).map((s) => this.outs[s][0]));
  }

  run(text: string): [boolean, number] {
    let current = this.closure([0]);
    let steps = current.length;
    for (const char of text) {
      current = this.advance(current, char);
      steps += current.length;
      if (current.length === 0) return [false, steps];
    }
    return [current.includes(this.final), steps];
  }

  // One pass: each live state carries the earliest start that reaches it, and the live list stays
  // ordered by start. After a match, later starts are dropped and the scan goes on while a state
  // with that start or an earlier one is alive.
  leftmostLongest(text: string): number[] {
    let best: [number, number] | null = null;
    let live: [number, number][] = [];
    for (let position = 0; position <= text.length; position++) {
      if (best === null) {
        const have = new Set(live.map(([state]) => state));
        for (const state of this.closure([0])) {
          if (!have.has(state)) live.push([state, position]);
        }
      }
      for (const [state, start] of live) {
        if (state === this.final && (best === null || start <= best[0])) best = [start, position];
      }
      if (best !== null) {
        const limit = best[0];
        live = live.filter(([, start]) => start <= limit);
      }
      if (position === text.length || live.length === 0) break;
      const seen = new Set<number>();
      const moved: [number, number][] = [];
      for (const [state, start] of live) {
        if (!this.accepts(state, text[position])) continue;
        for (const reached of this.closure([this.outs[state][0]])) {
          if (!seen.has(reached)) {
            seen.add(reached);
            moved.push([reached, start]);
          }
        }
      }
      live = moved;
    }
    return best === null ? [-1, -1] : [best[0], best[1]];
  }
}

export class RegexEngine {
  private automata = new Map<string, Automaton>();

  private automaton(pattern: string): Automaton {
    let automaton = this.automata.get(pattern);
    if (automaton === undefined) {
      automaton = new Automaton(new Parser(pattern).parse());
      this.automata.set(pattern, automaton);
    }
    return automaton;
  }

  // Level 1
  parse(pattern: string): string {
    try {
      return show(new Parser(pattern).parse());
    } catch (error) {
      if (error instanceof PatternError) return `error: ${error.code} at ${error.position}`;
      throw error;
    }
  }

  // Level 2
  nfa(pattern: string): string[] {
    const automaton = this.automaton(pattern);
    return automaton.kind.map((_, state) => automaton.line(state));
  }

  // Level 3
  fullMatch(pattern: string, text: string): boolean {
    return this.automaton(pattern).run(text)[0];
  }

  countSteps(pattern: string, text: string): number {
    return this.automaton(pattern).run(text)[1];
  }

  // Level 4
  search(pattern: string, text: string): number[] {
    return this.automaton(pattern).leftmostLongest(text);
  }
}
