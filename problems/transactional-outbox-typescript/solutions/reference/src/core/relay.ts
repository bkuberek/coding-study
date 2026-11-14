// Takes committed events out of the outbox and hands them to the broker. It never writes business
// state, and it can run again at any moment, so the worst it can do is send something twice.

import { PublishFailed, WriteFailed } from "./ports.ts";
import type { BrokerEvent, EventPublisher, OutboxRow, OutboxTable, UnitOfWork } from "./ports.ts";

function asEvent(row: OutboxRow): BrokerEvent {
  const { id, aggregateId, sequence, type, state } = row;
  return { id, aggregateId, sequence, type, state };
}

export class Relay {
  readonly #unit: UnitOfWork;
  readonly #outbox: OutboxTable;
  readonly #publisher: EventPublisher;

  constructor(unit: UnitOfWork, outbox: OutboxTable, publisher: EventPublisher) {
    this.#unit = unit;
    this.#outbox = outbox;
    this.#publisher = publisher;
  }

  /** One pass: up to `limit` publish attempts, oldest first. Answers how many rows it marked sent.
   * After a failure the rental's later rows wait for the next pass, and others carry on. */
  run(limit: number): number {
    const heldBack = new Set<string>();
    let attempts = 0;
    let sent = 0;
    for (const row of this.#outbox.pending()) {
      if (attempts === limit) {
        break;
      }
      if (heldBack.has(row.aggregateId)) {
        continue;
      }
      attempts += 1;
      try {
        this.#publisher.publish(asEvent(row));
        this.#unit.transaction(() => this.#outbox.markSent(row.id));
        sent += 1;
      } catch (error) {
        if (!(error instanceof PublishFailed || error instanceof WriteFailed)) {
          throw error;
        }
        heldBack.add(row.aggregateId);
      }
    }
    return sent;
  }
}
