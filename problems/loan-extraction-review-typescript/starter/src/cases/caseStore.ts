// The review cases, in memory. Each submission makes one.

import type { SourceDocument } from "../intake/document.ts";
import type { ExtractedValues } from "../intake/extraction.ts";

export interface ReviewCase {
  id: string;
  document: SourceDocument;
  values: ExtractedValues;
}

export class CaseStore {
  readonly #cases = new Map<string, ReviewCase>();

  /** Gives the case the next id: C-1, C-2 and so on. */
  add(document: SourceDocument, values: ExtractedValues): ReviewCase {
    const id = `C-${this.#cases.size + 1}`;
    const reviewCase = { id, document, values };
    this.#cases.set(id, reviewCase);
    return reviewCase;
  }

  find(id: string): ReviewCase | undefined {
    return this.#cases.get(id);
  }
}
