// The current result of each document, which the search pages read.

import type { Database, DocumentRow } from "./database.ts";

export class DocumentIndex {
  readonly #database: Database;

  constructor(database: Database) {
    this.#database = database;
  }

  save(row: DocumentRow): void {
    this.#database.transaction((tables) => {
      tables.documents.set(row.documentId, row);
    });
  }

  find(documentId: string): DocumentRow | undefined {
    return this.#database.read((tables) => tables.documents.get(documentId));
  }
}
