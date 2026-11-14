// The entry class: `cstudy` loads `Inventory` from `src/inventory.ts`.
//
// It imports its sibling module both ways a project may, by relative path and through the
// package's own `imports` map, and both must reach the same module.

import { labelFor as labelThroughPackage } from "#store/labels.ts";
import { labelFor } from "./labels.ts";

if (labelThroughPackage !== labelFor) {
  throw new Error("src/labels.ts was loaded twice, under two URLs");
}

export class Inventory {
  readonly #counts = new Map<string, number>();

  add(name: string, count: number): number {
    const total = (this.#counts.get(name) ?? 0) + count;
    this.#counts.set(name, total);
    return total;
  }

  label(name: string): string {
    return labelFor(name, this.#counts.get(name) ?? 0);
  }
}
