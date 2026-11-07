// The consumer process. The database outlives the process; everything else belongs to it.

import { Extractor } from "./extraction/extractor.ts";
import { canonicalJson } from "./json.ts";
import { Faults } from "./runtime/faults.ts";
import { Database } from "./storage/database.ts";
import { DocumentIndex } from "./storage/documentIndex.ts";
import { Ledger } from "./storage/ledger.ts";
import { DeliveryHandler } from "./worker/handler.ts";

export class DocumentConsumer {
  readonly #faults = new Faults();
  readonly #database = new Database(this.#faults);
  readonly #index = new DocumentIndex(this.#database);
  readonly #ledger = new Ledger(this.#database);
  readonly #handler = new DeliveryHandler(
    new Extractor(this.#faults),
    this.#index,
    this.#ledger,
  );

  /** One delivery from the broker. The answer is what the broker acts on. */
  deliver(delivery: string): string {
    return this.#handler.handle(delivery);
  }

  /** The document as JSON text with sorted keys, or "" for a document never seen. */
  document(documentId: string): string {
    const row = this.#index.find(documentId);
    return row === undefined ? "" : canonicalJson(row);
  }

  /** One line per extraction paid for, oldest first. */
  ledger(): string[] {
    return this.#ledger
      .rows()
      .map((row) => `${row.documentId} v${row.pipelineVersion} ${row.pages}p`);
  }
}
