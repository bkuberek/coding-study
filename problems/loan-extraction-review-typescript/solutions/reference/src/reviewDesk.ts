// The review desk. The model proposes, code validates, a person decides: submit runs everything that
// code can say, and a case goes through by itself only when every stated rule holds.

import { CaseStore } from "./cases/caseStore.ts";
import type { ReviewCase } from "./cases/caseStore.ts";
import { FIELD_NAMES } from "./intake/extraction.ts";
import { parseDocument } from "./intake/document.ts";
import { validateModelOutput } from "./intake/validateModelOutput.ts";
import { canonicalJson } from "./json.ts";
import { assess } from "./review/assessment.ts";
import { correct, decide, routeLine, writeAudit } from "./review/decisions.ts";

export class ReviewDesk {
  readonly #cases = new CaseStore();

  /** `document` and `modelOutput` are JSON text. Answers JSON text with sorted keys. */
  submit(document: string, modelOutput: string): string {
    const { errors, values } = validateModelOutput(modelOutput);
    const source = parseDocument(document);
    const assessment = values === null ? null : assess(source, values);
    const reasons = assessment === null ? ["schema_invalid"] : assessment.reasons;
    const autoApprovable = reasons.length === 0;
    const reviewCase = this.#cases.add({
      document: source,
      errors,
      values,
      assessment,
      reasons,
      autoApprovable,
      state: autoApprovable ? "auto_approved" : "awaiting_person",
      audit: [],
    });
    writeAudit(reviewCase, routeLine(reasons, autoApprovable));
    const status = values === null ? "rejected" : "accepted";
    return canonicalJson({ caseId: reviewCase.id, errors, status });
  }

  /** Each value with who it came from, as JSON text, or "" when the case has none. */
  values(caseId: string): string {
    const values = this.#cases.find(caseId)?.values;
    return values === undefined || values === null ? "" : canonicalJson(values);
  }

  citations(caseId: string): string[] {
    const reviewCase = this.#cases.find(caseId);
    const results = reviewCase?.assessment?.citations;
    if (reviewCase?.values === undefined || reviewCase.values === null || results === undefined) {
      return [];
    }
    const { values } = reviewCase;
    return FIELD_NAMES.map((field) => `${field} ${values[field].source} ${results.get(field)}`);
  }

  derived(caseId: string): string {
    const derived = this.#cases.find(caseId)?.assessment?.derived;
    return derived === undefined ? "" : canonicalJson(derived);
  }

  route(caseId: string): string {
    const reviewCase = this.#cases.find(caseId);
    if (reviewCase === undefined) {
      return "";
    }
    const route = reviewCase.autoApprovable ? "auto_approve" : "person";
    return canonicalJson({ reasons: reviewCase.reasons, route });
  }

  decide(caseId: string, reviewer: string, decision: string, note: string): string {
    const reviewCase = this.#cases.find(caseId);
    return reviewCase === undefined ? "refused:unknown_case" : decide(reviewCase, reviewer, decision, note);
  }

  status(caseId: string): string {
    return this.#cases.find(caseId)?.state ?? "unknown";
  }

  queue(): string[] {
    return this.#cases.awaitingPerson().map((reviewCase: ReviewCase) => reviewCase.id);
  }

  audit(caseId: string): string[] {
    return [...(this.#cases.find(caseId)?.audit ?? [])];
  }

  correct(caseId: string, reviewer: string, field: string, value: string, sourceField: string): string {
    const reviewCase = this.#cases.find(caseId);
    return reviewCase === undefined
      ? "refused:unknown_case"
      : correct(reviewCase, reviewer, field, value, sourceField);
  }
}
