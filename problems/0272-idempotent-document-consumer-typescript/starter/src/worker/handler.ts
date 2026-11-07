// Handles one delivery: extract, pay for it, publish the result.

import type { Extractor } from "../extraction/extractor.ts";
import type { DocumentIndex } from "../storage/documentIndex.ts";
import type { Ledger } from "../storage/ledger.ts";
import { parseDelivery } from "./delivery.ts";

export type Verdict = "ack" | "retry";

export class DeliveryHandler {
  readonly #extractor: Extractor;
  readonly #index: DocumentIndex;
  readonly #ledger: Ledger;

  constructor(extractor: Extractor, index: DocumentIndex, ledger: Ledger) {
    this.#extractor = extractor;
    this.#index = index;
    this.#ledger = ledger;
  }

  handle(text: string): Verdict {
    const delivery = parseDelivery(text);
    const extraction = this.#extractor.extract(delivery.body);
    this.#ledger.charge({
      documentId: delivery.documentId,
      pipelineVersion: delivery.pipelineVersion,
      pages: extraction.pages,
    });
    this.#index.save({
      documentId: delivery.documentId,
      revision: delivery.revision,
      pipelineVersion: delivery.pipelineVersion,
      pages: extraction.pages,
      words: extraction.words,
    });
    return "ack";
  }
}
