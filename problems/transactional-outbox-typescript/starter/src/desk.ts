// The rental desk: wires the core to its adapters and answers the outside world.

import { MemoryAudit, MemoryDatabase, MemoryRentals } from "./adapters/memoryDatabase.ts";
import { canonicalJson } from "./json.ts";
import { RentalService } from "./core/rentalService.ts";

export class RentalDesk {
  readonly #database = new MemoryDatabase();
  readonly #rentals = new MemoryRentals(this.#database);
  readonly #audit = new MemoryAudit(this.#database);
  readonly #service = new RentalService(this.#rentals, this.#audit);

  act(rentalId: string, action: string, actor: string): string {
    return this.#service.act(rentalId, action, actor);
  }

  /** The rental as JSON text with sorted keys, or "" when there is no such rental. */
  rental(rentalId: string): string {
    const rental = this.#rentals.find(rentalId);
    return rental === undefined ? "" : canonicalJson(rental);
  }

  audit(): string[] {
    return this.#audit
      .rows()
      .map((row) => `${row.rentalId} v${row.version} ${row.action} by ${row.actor}`);
  }

  failNextWrite(table: string): void {
    this.#database.failNextWrite(table);
  }
}
