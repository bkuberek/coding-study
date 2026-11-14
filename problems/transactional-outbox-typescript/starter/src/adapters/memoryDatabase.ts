// The database, in memory. Standing in for a real one, it has tables and it can fail. It has no
// transactions yet.

import { WriteFailed } from "../core/ports.ts";
import type { AuditRow, AuditTable, RentalTable } from "../core/ports.ts";
import type { Rental } from "../core/rental.ts";

export interface Tables {
  rentals: Map<string, Rental>;
  audit: AuditRow[];
}

export class MemoryDatabase {
  tables: Tables = { rentals: new Map(), audit: [] };
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
