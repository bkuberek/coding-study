// Another team's service, seen from outside: it hears events from the broker and keeps a count. A
// count is not idempotent, so it remembers the event ids it has applied.

import type { BrokerEvent } from "../core/ports.ts";

export class AvailabilityBoard {
  readonly #applied = new Set<string>();
  #rentalsOut = 0;

  receive(event: BrokerEvent): void {
    if (this.#applied.has(event.id)) {
      return;
    }
    this.#applied.add(event.id);
    if (event.state === "out") {
      this.#rentalsOut += 1;
    } else if (event.state === "returned") {
      this.#rentalsOut -= 1;
    }
  }

  rentalsOut(): number {
    return this.#rentalsOut;
  }

  eventsApplied(): number {
    return this.#applied.size;
  }
}
