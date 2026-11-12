// Generators are prefix token lists parsed into a small tree. One xorshift32 stream feeds a whole
// call, so every value is fixed by the seed and its position. Shrinking is greedy: from the
// failing value, take the first candidate that still fails, and start again from it, until no
// candidate fails. Candidates are built from the generator, so each one is a value the generator
// could have drawn: in range, long enough and through every filter. The stateful level runs each
// command sequence on the correct queue and on the buggy one and shrinks the sequence the same
// way, keeping only sequences whose commands are all allowed.

type Gen =
  | { kind: "int"; low: number; high: number }
  | { kind: "list"; min: number; max: number; element: Gen }
  | { kind: "pair"; first: Gen; second: Gen }
  | { kind: "filter"; name: string; inner: Gen };

type Value = number | Value[] | { first: Value; second: Value };

class GiveUp extends Error {}

class Random {
  state: number;
  discards = 0;
  limit: number;

  constructor(seed: number, limit: number) {
    this.state = seed | 0;
    this.limit = limit;
  }

  next(): number {
    let x = this.state;
    x ^= x << 13;
    x ^= x >>> 17;
    x ^= x << 5;
    this.state = x;
    return x >>> 0;
  }

  between(low: number, high: number): number {
    return low + (this.next() % (high - low + 1));
  }

  discard(): void {
    this.discards += 1;
    if (this.discards > this.limit) throw new GiveUp();
  }
}

function parse(tokens: string[], at: number): [Gen, number] {
  const head = tokens[at];
  if (head === "int") {
    return [{ kind: "int", low: Number(tokens[at + 1]), high: Number(tokens[at + 2]) }, at + 3];
  }
  if (head === "list") {
    const [element, end] = parse(tokens, at + 3);
    return [{ kind: "list", min: Number(tokens[at + 1]), max: Number(tokens[at + 2]), element }, end];
  }
  if (head === "pair") {
    const [first, middle] = parse(tokens, at + 1);
    const [second, end] = parse(tokens, middle);
    return [{ kind: "pair", first, second }, end];
  }
  const [inner, end] = parse(tokens, at + 2);
  return [{ kind: "filter", name: tokens[at + 1], inner }, end];
}

function generator(text: string): Gen {
  return parse(text.split(" "), 0)[0];
}

function draw(gen: Gen, rng: Random): Value {
  switch (gen.kind) {
    case "int":
      return rng.between(gen.low, gen.high);
    case "list": {
      const length = rng.between(gen.min, gen.max);
      const items: Value[] = [];
      for (let i = 0; i < length; i++) items.push(draw(gen.element, rng));
      return items;
    }
    case "pair": {
      const first = draw(gen.first, rng);
      return { first, second: draw(gen.second, rng) };
    }
    case "filter":
      for (;;) {
        const value = draw(gen.inner, rng);
        if (passesFilter(gen.name, value)) return value;
        rng.discard();
      }
  }
}

function text(value: Value): string {
  if (typeof value === "number") return String(value);
  if (Array.isArray(value)) return "[" + value.map(text).join(",") + "]";
  return "(" + text(value.first) + "," + text(value.second) + ")";
}

function passesFilter(name: string, value: Value): boolean {
  switch (name) {
    case "even":
      return (value as number) % 2 === 0;
    case "odd":
      return (value as number) % 2 !== 0;
    case "nonzero":
      return value !== 0;
    case "positive":
      return (value as number) > 0;
    case "nonempty":
      return (value as Value[]).length > 0;
    case "distinct": {
      const items = value as Value[];
      return new Set(items.map(text)).size === items.length;
    }
    default: {
      const pair = value as { first: Value; second: Value };
      return text(pair.first) !== text(pair.second);
    }
  }
}

function total(value: Value): number {
  if (typeof value === "number") return value;
  if (Array.isArray(value)) return value.reduce<number>((sum, item) => sum + total(item), 0);
  return total(value.first) + total(value.second);
}

function ordered(values: number[]): boolean {
  for (let i = 0; i + 1 < values.length; i++) if (values[i] > values[i + 1]) return false;
  return true;
}

function holds(prop: string, value: Value): boolean {
  const [name, argument] = prop.split(" ");
  const k = argument === undefined ? 0 : Number(argument);
  switch (name) {
    case "lt":
      return (value as number) < k;
    case "not-multiple":
      return (value as number) % k !== 0;
    case "sum-lt":
      return total(value) < k;
    case "len-lt":
      return (value as Value[]).length < k;
    case "ordered":
      return ordered(value as number[]);
    case "sort-ordered":
      return ordered([...(value as number[])].sort((a, b) => a - b));
    case "one-pass-ordered": {
      const items = [...(value as number[])];
      for (let i = 0; i + 1 < items.length; i++) {
        if (items[i] > items[i + 1]) [items[i], items[i + 1]] = [items[i + 1], items[i]];
      }
      return ordered(items);
    }
    case "max-from-zero": {
      const items = value as number[];
      let best = 0;
      for (const item of items) best = Math.max(best, item);
      return items.length === 0 || best === Math.max(...items);
    }
    case "keys-distinct": {
      const pairs = value as { first: Value; second: Value }[];
      return new Set(pairs.map((pair) => text(pair.first))).size === pairs.length;
    }
    default: {
      const first = new Map<string, string>();
      const last = new Map<string, string>();
      for (const pair of value as { first: Value; second: Value }[]) {
        const key = text(pair.first);
        if (!first.has(key)) first.set(key, text(pair.second));
        last.set(key, text(pair.second));
      }
      for (const [key, item] of first) if (last.get(key) !== item) return false;
      return true;
    }
  }
}

function intCandidates(low: number, high: number, value: number): number[] {
  const target = low > 0 ? low : high < 0 ? high : 0;
  if (value === target) return [];
  const found = [target];
  let step = Math.trunc((value - target) / 2);
  while (step !== 0) {
    found.push(value - step);
    step = Math.trunc(step / 2);
  }
  return found;
}

function withoutRepeats<T>(value: T, found: T[], show: (item: T) => string): T[] {
  const seen = new Set([show(value)]);
  const kept: T[] = [];
  for (const candidate of found) {
    const key = show(candidate);
    if (!seen.has(key)) {
      seen.add(key);
      kept.push(candidate);
    }
  }
  return kept;
}

function removals<T>(items: T[], shortest: number): T[][] {
  const n = items.length;
  const found: T[][] = [];
  for (let size = n; size >= 1; size = Math.floor(size / 2)) {
    if (n - size < shortest) continue;
    for (let start = 0; start + size <= n; start += size) {
      found.push([...items.slice(0, start), ...items.slice(start + size)]);
    }
  }
  return found;
}

function candidatesOf(gen: Gen, value: Value): Value[] {
  let found: Value[] = [];
  switch (gen.kind) {
    case "int":
      found = intCandidates(gen.low, gen.high, value as number);
      break;
    case "list": {
      const items = value as Value[];
      found = removals(items, gen.min);
      items.forEach((item, i) => {
        for (const smaller of candidatesOf(gen.element, item)) {
          found.push([...items.slice(0, i), smaller, ...items.slice(i + 1)]);
        }
      });
      break;
    }
    case "pair": {
      const pair = value as { first: Value; second: Value };
      for (const smaller of candidatesOf(gen.first, pair.first)) {
        found.push({ first: smaller, second: pair.second });
      }
      for (const smaller of candidatesOf(gen.second, pair.second)) {
        found.push({ first: pair.first, second: smaller });
      }
      break;
    }
    case "filter":
      found = candidatesOf(gen.inner, value).filter((candidate) => passesFilter(gen.name, candidate));
      break;
  }
  return withoutRepeats(value, found, text);
}

class Queue {
  capacity: number;
  bug: string;
  items: number[] = [];
  puts = 0;

  constructor(capacity: number, bug: string) {
    this.capacity = capacity;
    this.bug = bug;
  }

  allows(command: string): boolean {
    return command !== "get" || this.items.length > 0;
  }

  apply(command: string): string {
    if (command === "size") {
      const count = this.items.length;
      return String(this.bug === "size-wraps" ? count % this.capacity : count);
    }
    if (command === "get") {
      if (this.items.length === 0) return "empty";
      if (this.bug === "wrap-lifo" && this.puts > this.capacity) return String(this.items.pop());
      return String(this.items.shift());
    }
    const value = Number(command.slice(4));
    if (this.items.length === this.capacity) {
      if (this.bug !== "full-overwrites") return "full";
      this.items.shift();
    } else if (
      this.bug === "repeat-dropped" &&
      this.items.length > 0 &&
      this.items[this.items.length - 1] === value
    ) {
      this.puts += 1;
      return "ok";
    }
    this.items.push(value);
    this.puts += 1;
    return "ok";
  }
}

function valid(capacity: number, commands: string[]): boolean {
  const model = new Queue(capacity, "none");
  for (const command of commands) {
    if (!model.allows(command)) return false;
    model.apply(command);
  }
  return true;
}

function fails(capacity: number, bug: string, commands: string[]): boolean {
  const model = new Queue(capacity, "none");
  const system = new Queue(capacity, bug);
  return commands.some((command) => model.apply(command) !== system.apply(command));
}

function sequence(capacity: number, rng: Random, longest: number): string[] {
  const model = new Queue(capacity, "none");
  const commands: string[] = [];
  const length = rng.between(1, longest);
  for (let i = 0; i < length; i++) {
    const allowed = model.items.length > 0 ? ["put", "get", "size"] : ["put", "size"];
    let command = allowed[rng.next() % allowed.length];
    if (command === "put") command = `put ${rng.between(0, 9)}`;
    model.apply(command);
    commands.push(command);
  }
  return commands;
}

function sequenceCandidates(capacity: number, commands: string[]): string[][] {
  const found = removals(commands, 1);
  commands.forEach((command, i) => {
    if (!command.startsWith("put ")) return;
    for (const smaller of intCandidates(0, 9, Number(command.slice(4)))) {
      found.push([...commands.slice(0, i), `put ${smaller}`, ...commands.slice(i + 1)]);
    }
  });
  return withoutRepeats(commands, found, (candidate) => candidate.join(", ")).filter((candidate) =>
    valid(capacity, candidate),
  );
}

type Outcome =
  | { kind: "failed"; run: number; value: Value }
  | { kind: "gave up"; run: number }
  | { kind: "passed" };

export class PropertyRunner {
  private limit = 100;

  // Level 1
  randoms(seed: number, count: number): number[] {
    const rng = new Random(seed, this.limit);
    const numbers: number[] = [];
    for (let i = 0; i < count; i++) numbers.push(rng.next());
    return numbers;
  }

  generate(gen: string, seed: number, count: number): string[] {
    const rng = new Random(seed, this.limit);
    const parsed = generator(gen);
    const values: string[] = [];
    try {
      for (let i = 0; i < count; i++) values.push(text(draw(parsed, rng)));
    } catch (error) {
      if (!(error instanceof GiveUp)) throw error;
    }
    return values;
  }

  check(gen: string, prop: string, seed: number, runs: number): string {
    const outcome = this.search(gen, prop, seed, runs);
    if (outcome.kind === "failed") return `failed ${outcome.run}: ${text(outcome.value)}`;
    if (outcome.kind === "gave up") return `gave up after ${outcome.run}`;
    return `passed ${runs}`;
  }

  // Level 2
  candidates(gen: string, seed: number, index: number): string[] {
    const rng = new Random(seed, this.limit);
    const parsed = generator(gen);
    let value: Value = 0;
    try {
      for (let i = 0; i < index; i++) value = draw(parsed, rng);
    } catch (error) {
      if (error instanceof GiveUp) return [];
      throw error;
    }
    return candidatesOf(parsed, value).map(text);
  }

  minimize(gen: string, prop: string, seed: number, runs: number): string[] {
    const outcome = this.search(gen, prop, seed, runs);
    if (outcome.kind !== "failed") return [];
    const parsed = generator(gen);
    let value = outcome.value;
    const path = [text(value)];
    for (;;) {
      const smaller = candidatesOf(parsed, value).find((candidate) => !holds(prop, candidate));
      if (smaller === undefined) return path;
      value = smaller;
      path.push(text(value));
    }
  }

  // Level 3
  setDiscardLimit(limit: number): void {
    this.limit = limit;
  }

  // Level 4
  replay(capacity: number, bug: string, commands: string[]): string[] {
    const model = new Queue(capacity, "none");
    const system = new Queue(capacity, bug);
    const answers: string[] = [];
    for (const command of commands) {
      if (!model.allows(command)) {
        answers.push("invalid");
        break;
      }
      model.apply(command);
      answers.push(system.apply(command));
    }
    return answers;
  }

  generateCommands(capacity: number, seed: number, count: number, maxLength: number): string[] {
    const rng = new Random(seed, this.limit);
    const sequences: string[] = [];
    for (let i = 0; i < count; i++) sequences.push(sequence(capacity, rng, maxLength).join(", "));
    return sequences;
  }

  firstFailure(capacity: number, bug: string, seed: number, runs: number, maxLength: number): string[] {
    const rng = new Random(seed, this.limit);
    for (let i = 0; i < runs; i++) {
      const commands = sequence(capacity, rng, maxLength);
      if (fails(capacity, bug, commands)) return commands;
    }
    return [];
  }

  shrinkFailure(capacity: number, bug: string, seed: number, runs: number, maxLength: number): string[] {
    let commands = this.firstFailure(capacity, bug, seed, runs, maxLength);
    while (commands.length > 0) {
      const smaller = sequenceCandidates(capacity, commands).find((candidate) =>
        fails(capacity, bug, candidate),
      );
      if (smaller === undefined) break;
      commands = smaller;
    }
    return commands;
  }

  private search(gen: string, prop: string, seed: number, runs: number): Outcome {
    const rng = new Random(seed, this.limit);
    const parsed = generator(gen);
    let passed = 0;
    try {
      for (let run = 1; run <= runs; run++) {
        const value = draw(parsed, rng);
        if (!holds(prop, value)) return { kind: "failed", run, value };
        passed += 1;
      }
    } catch (error) {
      if (error instanceof GiveUp) return { kind: "gave up", run: passed };
      throw error;
    }
    return { kind: "passed" };
  }
}
