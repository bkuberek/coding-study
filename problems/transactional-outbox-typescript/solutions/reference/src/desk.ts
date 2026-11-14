// The rental desk: wires the core to its adapters and answers the outside world.

import { FakeBroker } from "./adapters/fakeBroker.ts";
import { MemoryAudit, MemoryDatabase, MemoryOutbox, MemoryRentals } from "./adapters/memoryDatabase.ts";
import { Relay } from "./core/relay.ts";
import { RentalService } from "./core/rentalService.ts";
import { AvailabilityBoard } from "./downstream/availabilityBoard.ts";
import { canonicalJson } from "./json.ts";

export class RentalDesk {
  readonly #database = new MemoryDatabase();
  readonly #rentals = new MemoryRentals(this.#database);
  readonly #audit = new MemoryAudit(this.#database);
  readonly #outbox = new MemoryOutbox(this.#database);
  readonly #service = new RentalService(this.#database, this.#rentals, this.#audit, this.#outbox);
  readonly #broker = new FakeBroker();
  readonly #relay = new Relay(this.#database, this.#outbox, this.#broker);
  readonly #board = new AvailabilityBoard();

  constructor() {
    this.#broker.subscribe((event) => this.#board.receive(event));
  }

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

  outbox(): string[] {
    return this.#outbox.rows().map((row) => canonicalJson(row));
  }

  relay(limit: number): number {
    return this.#relay.run(limit);
  }

  published(): string[] {
    return this.#broker
      .log()
      .map((event) => `${event.id} ${event.aggregateId} #${event.sequence} ${event.state}`);
  }

  failNextPublish(rentalId: string, times: number): void {
    this.#broker.refuseNext(rentalId, times);
  }

  loseNextAck(rentalId: string): void {
    this.#broker.loseNextAck(rentalId);
  }

  rentalsOut(): number {
    return this.#board.rentalsOut();
  }

  eventsApplied(): number {
    return this.#board.eventsApplied();
  }

  prune(): number {
    return this.#database.transaction(() => this.#outbox.deleteSent());
  }
}
