// The review cases, in memory. Each submission makes one, including one the schema rejected: that
// document still has to go somewhere.

import type { SourceDocument } from "../intake/document.ts";
import type { ExtractedValues } from "../intake/extraction.ts";
import type { Assessment } from "../review/assessment.ts";

export type CaseState = "auto_approved" | "awaiting_person" | "approved_by_person" | "declined_by_person";

export interface ReviewCase {
  id: string;
  document: SourceDocument;
  errors: string[];
  values: ExtractedValues | null;
  assessment: Assessment | null;
  reasons: string[];
  /** False from the first correction on: only values no person has touched can auto-approve. */
  autoApprovable: boolean;
  state: CaseState;
  /** Text only, and only ever appended to. */
  audit: string[];
}

export class CaseStore {
  readonly #cases = new Map<string, ReviewCase>();

  add(fields: Omit<ReviewCase, "id">): ReviewCase {
    const id = `C-${this.#cases.size + 1}`;
    const reviewCase = { ...fields, id };
    this.#cases.set(id, reviewCase);
    return reviewCase;
  }

  find(id: string): ReviewCase | undefined {
    return this.#cases.get(id);
  }

  /** The cases waiting for a person, oldest first. */
  awaitingPerson(): ReviewCase[] {
    return [...this.#cases.values()].filter((reviewCase) => reviewCase.state === "awaiting_person");
  }
}
