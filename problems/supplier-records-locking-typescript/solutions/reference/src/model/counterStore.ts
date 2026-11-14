// Counters, in memory. Every successful change takes the next version, including a change to the
// same value and an add: the version says "something happened", which the value cannot.

export interface Counter {
  name: string;
  value: number;
  version: number;
}

export const SEED_COUNTERS: readonly Counter[] = [
  { name: "open-orders", value: 5, version: 1 },
  { name: "late-orders", value: 0, version: 1 },
];

export class CounterStore {
  readonly #counters = new Map<string, Counter>();

  constructor(seed: readonly Counter[]) {
    for (const counter of seed) {
      this.#counters.set(counter.name, { ...counter });
    }
  }

  find(name: string): Counter | undefined {
    return this.#counters.get(name);
  }

  write(current: Counter, value: number): Counter {
    const next = { ...current, value, version: current.version + 1 };
    this.#counters.set(current.name, next);
    return next;
  }
}
