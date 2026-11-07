// What the core needs from the outside world. The adapters implement these.

import type { Rental } from "./rental.ts";

export interface AuditRow {
  rentalId: string;
  version: number;
  action: string;
  actor: string;
}

export interface NewEvent {
  aggregateId: string;
  sequence: number;
  type: string;
  state: string;
}

export interface OutboxRow extends NewEvent {
  id: string;
  status: "pending" | "sent";
}

export interface RentalTable {
  /** The stored row itself, not a copy. */
  find(id: string): Rental | undefined;
  save(rental: Rental): void;
}

export interface AuditTable {
  append(row: AuditRow): void;
  rows(): AuditRow[];
}

export interface OutboxTable {
  /** Adds a pending row and gives it the next event number. */
  append(event: NewEvent): void;
  rows(): OutboxRow[];
  /** A copy of the pending rows, oldest first. */
  pending(): OutboxRow[];
  markSent(id: string): void;
  /** Deletes the rows already sent, and says how many. */
  deleteSent(): number;
}

/** Commits what `work` wrote when it returns; undoes all of it when it throws. */
export interface UnitOfWork {
  transaction<T>(work: () => T): T;
}

/** An event as the broker carries it. */
export interface BrokerEvent {
  id: string;
  aggregateId: string;
  sequence: number;
  type: string;
  state: string;
}

/** Hands one event to the broker, or throws `PublishFailed`. */
export interface EventPublisher {
  publish(event: BrokerEvent): void;
}

/** The broker did not confirm. The caller cannot tell whether it took the message. */
export class PublishFailed extends Error {
  constructor(eventId: string) {
    super(`no confirmation for ${eventId}`);
    this.name = "PublishFailed";
  }
}

/** A write the database refused. */
export class WriteFailed extends Error {
  constructor(table: string) {
    super(`write to ${table} failed`);
    this.name = "WriteFailed";
  }
}
