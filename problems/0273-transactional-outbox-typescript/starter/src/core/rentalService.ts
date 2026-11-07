// The one use case the desk has: someone does something to a rental.

import type { AuditTable, RentalTable } from "./ports.ts";
import { nextState } from "./rental.ts";

export type Outcome = "ok" | "refused" | "failed";

export class RentalService {
  readonly #rentals: RentalTable;
  readonly #audit: AuditTable;

  constructor(rentals: RentalTable, audit: AuditTable) {
    this.#rentals = rentals;
    this.#audit = audit;
  }

  act(rentalId: string, action: string, actor: string): Outcome {
    const rental = this.#rentals.find(rentalId);
    const next = nextState(action, rental?.state ?? null);
    if (next === null) {
      return "refused";
    }
    const updated = rental ?? { id: rentalId, state: next, version: 0 };
    updated.state = next;
    updated.version += 1;
    this.#rentals.save(updated);
    this.#audit.append({ rentalId, version: updated.version, action, actor });
    return "ok";
  }
}
