// What the core needs from the outside world. The adapters implement these.

import type { Rental } from "./rental.ts";

export interface AuditRow {
  rentalId: string;
  version: number;
  action: string;
  actor: string;
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

/** An event as the broker carries it. */
export interface BrokerEvent {
  id: string;
  aggregateId: string;
  sequence: number;
  type: string;
  state: string;
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
