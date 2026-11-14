// The hot desks the space holds itself: how many are left on each day it sells.

import { readFile } from "node:fs/promises";

export class DeskInventory {
  readonly #byDay: Map<string, number>;

  constructor(byDay: Map<string, number>) {
    this.#byDay = byDay;
  }

  static async fromFile(path: string): Promise<DeskInventory> {
    const seeded = JSON.parse(await readFile(path, "utf8")) as Record<string, number>;
    return new DeskInventory(new Map(Object.entries(seeded)));
  }

  availableOn(day: string): number | undefined {
    return this.#byDay.get(day);
  }
}
