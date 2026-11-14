// The current result of each document, which the search pages read.

import type { Database, DocumentRow } from "./database.ts";

export class DocumentIndex {
  readonly #database: Database;

  constructor(database: Database) {
    this.#database = database;
  }

  find(documentId: string): DocumentRow | undefined {
    return this.#database.read((tables) => tables.documents.get(documentId));
  }
}
