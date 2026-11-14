// The database, in memory. Standing in for a real one, it has tables, it can fail, and it has
// transactions: a copy of every row on the way in, put back on the way out when the work throws.

import { WriteFailed } from "../core/ports.ts";
import type {
  AuditRow,
  AuditTable,
  NewEvent,
  OutboxRow,
  OutboxTable,
  RentalTable,
  UnitOfWork,
} from "../core/ports.ts";
import type { Rental } from "../core/rental.ts";

export interface Tables {
  rentals: Map<string, Rental>;
  audit: AuditRow[];
  outbox: OutboxRow[];
  /** How many outbox rows were ever committed. A table's sequence, not its size. */
  eventsWritten: number;
}

export class MemoryDatabase implements UnitOfWork {
  tables: Tables = { rentals: new Map(), audit: [], outbox: [], eventsWritten: 0 };
  #failingTable: string | null = null;

  /** The next write to `table` throws `WriteFailed`. */
  failNextWrite(table: string): void {
    this.#failingTable = table;
  }

  /** Every write to a table calls this first. */
  beforeWrite(table: string): void {
    if (this.#failingTable === table) {
      this.#failingTable = null;
      throw new WriteFailed(table);
    }
  }

  transaction<T>(work: () => T): T {
    const snapshot = structuredClone(this.tables);
    try {
      return work();
    } catch (error) {
      this.tables = snapshot;
      throw error;
    }
  }
}

export class MemoryRentals implements RentalTable {
  readonly #database: MemoryDatabase;

  constructor(database: MemoryDatabase) {
    this.#database = database;
  }

  find(id: string): Rental | undefined {
    return this.#database.tables.rentals.get(id);
  }

  save(rental: Rental): void {
    this.#database.beforeWrite("rentals");
    this.#database.tables.rentals.set(rental.id, rental);
  }
}

export class MemoryAudit implements AuditTable {
  readonly #database: MemoryDatabase;

  constructor(database: MemoryDatabase) {
    this.#database = database;
  }

  append(row: AuditRow): void {
    this.#database.beforeWrite("audit");
    this.#database.tables.audit.push(row);
  }

  rows(): AuditRow[] {
    return this.#database.tables.audit;
  }
}

export class MemoryOutbox implements OutboxTable {
  readonly #database: MemoryDatabase;

  constructor(database: MemoryDatabase) {
    this.#database = database;
  }

  append(event: NewEvent): void {
    this.#database.beforeWrite("outbox");
    const { tables } = this.#database;
    tables.eventsWritten += 1;
    tables.outbox.push({ ...event, id: `evt-${tables.eventsWritten}`, status: "pending" });
  }

  rows(): OutboxRow[] {
    return this.#database.tables.outbox;
  }

  pending(): OutboxRow[] {
    return this.#database.tables.outbox.filter((row) => row.status === "pending");
  }

  markSent(id: string): void {
    this.#database.beforeWrite("outbox");
    const row = this.#database.tables.outbox.find((candidate) => candidate.id === id);
    if (row !== undefined) {
      row.status = "sent";
    }
  }

  deleteSent(): number {
    const { tables } = this.#database;
    const kept = tables.outbox.filter((row) => row.status !== "sent");
    const deleted = tables.outbox.length - kept.length;
    tables.outbox = kept;
    return deleted;
  }
}
