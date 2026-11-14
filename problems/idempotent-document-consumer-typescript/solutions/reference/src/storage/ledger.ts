// What we owe for extraction: one row per extraction paid for, reconciled against the invoice.

import type { Database, LedgerRow } from "./database.ts";

export class Ledger {
  readonly #database: Database;

  constructor(database: Database) {
    this.#database = database;
  }

  rows(): LedgerRow[] {
    return this.#database.read((tables) => [...tables.ledger]);
  }
}
