// The one use case the desk has: someone does something to a rental. The state, the audit row and
// the event are one commit: there is no moment when one of them is true and the others are not.

import { WriteFailed } from "./ports.ts";
import type { AuditTable, OutboxTable, RentalTable, UnitOfWork } from "./ports.ts";
import { eventType, nextState } from "./rental.ts";

export type Outcome = "ok" | "refused" | "failed";

export class RentalService {
  readonly #unit: UnitOfWork;
  readonly #rentals: RentalTable;
  readonly #audit: AuditTable;
  readonly #outbox: OutboxTable;

  constructor(unit: UnitOfWork, rentals: RentalTable, audit: AuditTable, outbox: OutboxTable) {
    this.#unit = unit;
    this.#rentals = rentals;
    this.#audit = audit;
    this.#outbox = outbox;
  }

  act(rentalId: string, action: string, actor: string): Outcome {
    try {
      return this.#unit.transaction(() => this.#apply(rentalId, action, actor));
    } catch (error) {
      if (error instanceof WriteFailed) {
        return "failed";
      }
      throw error;
    }
  }

  #apply(rentalId: string, action: string, actor: string): Outcome {
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
    this.#outbox.append({
      aggregateId: rentalId,
      sequence: updated.version,
      type: eventType(action),
      state: next,
    });
    return "ok";
  }
}
