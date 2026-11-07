// The consumer process. The database outlives the process; everything else belongs to it.

import { Extractor } from "./extraction/extractor.ts";
import { canonicalJson } from "./json.ts";
import { Faults, ProcessCrash } from "./runtime/faults.ts";
import { Database } from "./storage/database.ts";
import { DocumentIndex } from "./storage/documentIndex.ts";
import { Ledger } from "./storage/ledger.ts";
import { DeliveryHandler } from "./worker/handler.ts";

export class DocumentConsumer {
  readonly #faults = new Faults();
  readonly #database = new Database(this.#faults);
  readonly #index = new DocumentIndex(this.#database);
  readonly #ledger = new Ledger(this.#database);
  #handler = this.#newHandler();

  /** One delivery from the broker. The answer is what the broker acts on. */
  deliver(delivery: string): string {
    try {
      const verdict = this.#handler.handle(delivery);
      this.#faults.crashIfArmed("before-ack");
      return verdict;
    } catch (error) {
      if (error instanceof ProcessCrash) {
        return "crashed";
      }
      throw error;
    }
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

  failExtractions(times: number): void {
    this.#faults.failExtractions(times);
  }

  deadLetters(): string[] {
    return this.#database.read((tables) => [...tables.deadLetters]);
  }

  crashAt(point: string): void {
    this.#faults.armCrash(point);
  }

  /** A new process over the same database: nothing else survives. */
  restart(): void {
    this.#handler = this.#newHandler();
  }

  #newHandler(): DeliveryHandler {
    return new DeliveryHandler(new Extractor(this.#faults), this.#database);
  }
}
