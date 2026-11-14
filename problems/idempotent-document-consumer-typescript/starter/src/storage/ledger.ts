// What we owe for extraction: one row per extraction paid for, reconciled against the invoice.

import type { Database, LedgerRow } from "./database.ts";

export class Ledger {
  readonly #database: Database;

  constructor(database: Database) {
    this.#database = database;
  }

  charge(row: LedgerRow): void {
    this.#database.transaction((tables) => {
      tables.ledger.push(row);
    });
  }

  rows(): LedgerRow[] {
    return this.#database.read((tables) => [...tables.ledger]);
  }
}
