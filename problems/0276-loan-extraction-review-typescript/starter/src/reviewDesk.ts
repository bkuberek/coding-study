// The review desk takes an extraction from the model and keeps it. It takes it on trust, for now.

import { CaseStore } from "./cases/caseStore.ts";
import { parseDocument } from "./intake/document.ts";
import type { ExtractedValues } from "./intake/extraction.ts";
import { canonicalJson } from "./json.ts";

export class ReviewDesk {
  readonly #cases = new CaseStore();

  /** `document` and `modelOutput` are JSON text. Answers JSON text with sorted keys. */
  submit(document: string, modelOutput: string): string {
    const output = JSON.parse(modelOutput) as { values: ExtractedValues };
    const reviewCase = this.#cases.add(parseDocument(document), output.values);
    return canonicalJson({ caseId: reviewCase.id, errors: [], status: "accepted" });
  }

  /** Each value with who it came from, as JSON text, or "" when the case has none. */
  values(caseId: string): string {
    const reviewCase = this.#cases.find(caseId);
    if (reviewCase === undefined) {
      return "";
    }
    const entries = Object.entries(reviewCase.values);
    return canonicalJson(Object.fromEntries(entries.map(([name, entry]) => [name, { by: "model", ...entry }])));
  }
}
