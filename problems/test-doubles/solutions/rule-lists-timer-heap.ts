// Every double keeps its stub rules per method, newest last, and a mock also keeps its
// expectations in the order they were set. One log holds every call in the order it was made,
// with its time, and each double keeps the positions of its own calls in that log, so the spy
// questions read short lists. Timers wait in a binary heap ordered by due time, then by the
// sequence number they got when they were last put in, so equal times fire in scheduling order.

const UNKNOWN = "!unknown";
const UNEXPECTED = "!unexpected";

function fits(pattern: string[], args: string[]): boolean {
  return pattern.length === args.length && pattern.every((p, i) => p === "*" || p === args[i]);
}

class Rule {
  pattern: string[];
  answers: string[];
  used = 0;

  constructor(pattern: string[], answers: string[]) {
    this.pattern = pattern;
    this.answers = answers;
  }

  nextAnswer(): string {
    const answer = this.answers[Math.min(this.used, this.answers.length - 1)];
    this.used += 1;
    return answer;
  }
}

interface Expectation {
  method: string;
  pattern: string[];
  answer: string;
  times: number;
  used: number;
}

class Double {
  mock: boolean;
  strict: boolean;
  rules = new Map<string, Rule[]>();
  fallback = new Map<string, string>();
  expectations: Expectation[] = [];
  unexpected: [string, string[]][] = [];
  calls: number[] = [];

  constructor(mock: boolean, strict: boolean) {
    this.mock = mock;
    this.strict = strict;
  }

  answer(method: string, args: string[]): string {
    for (const e of this.expectations) {
      if (e.method === method && e.used < e.times && fits(e.pattern, args)) {
        e.used += 1;
        return e.answer;
      }
    }
    const rules = this.rules.get(method) ?? [];
    for (let i = rules.length - 1; i >= 0; i--) {
      if (fits(rules[i].pattern, args)) return rules[i].nextAnswer();
    }
    const fallback = this.fallback.get(method);
    if (fallback !== undefined) return fallback;
    if (!this.mock) return "";
    this.unexpected.push([method, args]);
    return this.strict ? UNEXPECTED : "";
  }
}

interface LoggedCall {
  name: string;
  method: string;
  args: string[];
  time: number;
}

interface Timer {
  name: string;
  method: string;
  args: string[];
  interval: number;
  stopped: boolean;
}

// An entry of the timer heap: [due, sequence, id], smallest first.
type Entry = [number, number, number];

function before(a: Entry, b: Entry): boolean {
  return a[0] !== b[0] ? a[0] < b[0] : a[1] < b[1];
}

class Heap {
  items: Entry[] = [];

  push(entry: Entry): void {
    const items = this.items;
    items.push(entry);
    let i = items.length - 1;
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (!before(items[i], items[parent])) break;
      [items[i], items[parent]] = [items[parent], items[i]];
      i = parent;
    }
  }

  pop(): Entry {
    const items = this.items;
    const top = items[0];
    const last = items.pop()!;
    if (items.length > 0) {
      items[0] = last;
      let i = 0;
      for (;;) {
        const left = 2 * i + 1;
        const right = left + 1;
        let smallest = i;
        if (left < items.length && before(items[left], items[smallest])) smallest = left;
        if (right < items.length && before(items[right], items[smallest])) smallest = right;
        if (smallest === i) break;
        [items[i], items[smallest]] = [items[smallest], items[i]];
        i = smallest;
      }
    }
    return top;
  }
}

export class Doubles {
  private doubles = new Map<string, Double>();
  private log: LoggedCall[] = [];
  private clock = 0;
  private heap = new Heap();
  private timers: Timer[] = [];
  private sequence = 0;

  // Level 1
  addStub(name: string): boolean {
    return this.add(name, false, false);
  }

  onCall(name: string, method: string, args: string[], answers: string[]): boolean {
    const double = this.doubles.get(name);
    if (double === undefined) return false;
    const rules = double.rules.get(method) ?? [];
    rules.push(new Rule([...args], [...answers]));
    double.rules.set(method, rules);
    return true;
  }

  otherwise(name: string, method: string, answer: string): boolean {
    const double = this.doubles.get(name);
    if (double === undefined) return false;
    double.fallback.set(method, answer);
    return true;
  }

  call(name: string, method: string, args: string[]): string {
    const double = this.doubles.get(name);
    if (double === undefined) return UNKNOWN;
    double.calls.push(this.log.length);
    this.log.push({ name, method, args: [...args], time: this.clock });
    return double.answer(method, [...args]);
  }

  // Level 2
  callCount(name: string, method: string): number {
    return this.count(name, method, null);
  }

  matchCount(name: string, method: string, args: string[]): number {
    return this.count(name, method, args);
  }

  nthCall(name: string, n: number): string[] {
    const double = this.doubles.get(name);
    if (double === undefined || n === 0 || Math.abs(n) > double.calls.length) return [];
    const position = double.calls[n > 0 ? n - 1 : double.calls.length + n];
    const call = this.log[position];
    return [call.method, ...call.args];
  }

  inOrder(steps: string[][]): boolean {
    let step = 0;
    for (const call of this.log) {
      if (step === steps.length) break;
      const wanted = steps[step];
      if (wanted[0] === call.name && wanted[1] === call.method && fits(wanted.slice(2), call.args)) {
        step += 1;
      }
    }
    return step === steps.length;
  }

  // Level 3
  addMock(name: string, strict: boolean): boolean {
    return this.add(name, true, strict);
  }

  expect(name: string, method: string, args: string[], answer: string, times: number): boolean {
    const double = this.doubles.get(name);
    if (double === undefined || !double.mock) return false;
    double.expectations.push({ method, pattern: [...args], answer, times, used: 0 });
    return true;
  }

  verify(name: string): string[] {
    const double = this.doubles.get(name);
    if (double === undefined) return [UNKNOWN];
    const report: string[] = [];
    for (const e of double.expectations) {
      if (e.used < e.times) {
        report.push(`missing ${name}.${e.method}(${e.pattern.join(",")}) ${e.used}/${e.times}`);
      }
    }
    for (const [method, args] of double.unexpected) {
      report.push(`unexpected ${name}.${method}(${args.join(",")})`);
    }
    return report;
  }

  verifyAll(): string[] {
    const report: string[] = [];
    for (const [name, double] of this.doubles) {
      if (double.mock) report.push(...this.verify(name));
    }
    return report;
  }

  // Level 4
  now(): number {
    return this.clock;
  }

  schedule(delay: number, name: string, method: string, args: string[]): number {
    return this.timer(delay, 0, name, method, args);
  }

  every(interval: number, name: string, method: string, args: string[]): number {
    return this.timer(interval, interval, name, method, args);
  }

  cancel(timerId: number): boolean {
    const timer = this.timers[timerId - 1];
    if (timer === undefined || timer.stopped) return false;
    timer.stopped = true;
    return true;
  }

  advance(ms: number): string[] {
    const end = this.clock + ms;
    const fired: string[] = [];
    while (this.heap.items.length > 0 && this.heap.items[0][0] <= end) {
      const [due, , timerId] = this.heap.pop();
      const timer = this.timers[timerId - 1];
      if (timer.stopped) continue;
      this.clock = due;
      if (timer.interval > 0) {
        this.push(due + timer.interval, timerId);
      } else {
        timer.stopped = true;
      }
      fired.push(`${timerId}@${due}`);
      this.call(timer.name, timer.method, timer.args);
    }
    this.clock = end;
    return fired;
  }

  pending(): string[] {
    const live = this.heap.items.filter((entry) => !this.timers[entry[2] - 1].stopped);
    live.sort((a, b) => (before(a, b) ? -1 : 1));
    return live.map(([due, , timerId]) => `${timerId}@${due}`);
  }

  callTimes(name: string, method: string): number[] {
    const double = this.doubles.get(name);
    if (double === undefined) return [];
    return double.calls
      .filter((position) => this.log[position].method === method)
      .map((position) => this.log[position].time);
  }

  private count(name: string, method: string, pattern: string[] | null): number {
    const double = this.doubles.get(name);
    if (double === undefined) return -1;
    let total = 0;
    for (const position of double.calls) {
      const call = this.log[position];
      if (call.method === method && (pattern === null || fits(pattern, call.args))) total += 1;
    }
    return total;
  }

  private add(name: string, mock: boolean, strict: boolean): boolean {
    if (this.doubles.has(name)) return false;
    this.doubles.set(name, new Double(mock, strict));
    return true;
  }

  private timer(delay: number, interval: number, name: string, method: string, args: string[]): number {
    if (!this.doubles.has(name)) return -1;
    this.timers.push({ name, method, args: [...args], interval, stopped: false });
    this.push(this.clock + delay, this.timers.length);
    return this.timers.length;
  }

  private push(due: number, timerId: number): void {
    this.sequence += 1;
    this.heap.push([due, this.sequence, timerId]);
  }
}
