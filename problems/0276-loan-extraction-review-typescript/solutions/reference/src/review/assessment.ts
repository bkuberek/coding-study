// Everything code can say about an extraction: a pure function of the document and the values, so
// it can run again after a person changes something, and it cannot disagree with itself.

import type { CitationResult } from "../checks/citations.ts";
import { citationsOf } from "../checks/citations.ts";
import type { SourceDocument } from "../intake/document.ts";
import { FIELD_NAMES } from "../intake/extraction.ts";
import type { ExtractedValues, FieldName } from "../intake/extraction.ts";
import { derive } from "../money/loanMath.ts";
import type { Derived } from "../money/loanMath.ts";

const MIN_CONFIDENCE = 0.9;
const AUTO_APPROVE_LIMIT_CENTS = 5_000_000;
const MAX_PAYMENT_TO_INCOME_BPS = 3500;

export interface Assessment {
  citations: Map<FieldName, CitationResult>;
  derived: Derived;
  reasons: string[];
}

export function assess(document: SourceDocument, values: ExtractedValues): Assessment {
  const number = (field: FieldName) => values[field].value as number;
  const citations = citationsOf(document, values);
  const derived = derive(
    number("amountCents"),
    number("rateBps"),
    number("termMonths"),
    number("monthlyIncomeCents"),
    number("statedPaymentCents"),
  );

  const reasons: string[] = [];
  for (const field of FIELD_NAMES) {
    if (citations.get(field) !== "ok") {
      reasons.push(`citation_failed:${field}`);
    }
  }
  for (const field of FIELD_NAMES) {
    const { confidence } = values[field];
    if (confidence !== null && confidence < MIN_CONFIDENCE) {
      reasons.push(`low_confidence:${field}`);
    }
  }
  if (!derived.statedPaymentMatches) {
    reasons.push("payment_mismatch");
  }
  if (number("amountCents") > AUTO_APPROVE_LIMIT_CENTS) {
    reasons.push("amount_over_limit");
  }
  if (derived.paymentToIncomeBps > MAX_PAYMENT_TO_INCOME_BPS) {
    reasons.push("payment_to_income_high");
  }
  if (number("rateBps") === 0) {
    reasons.push("zero_rate");
  }
  return { citations, derived, reasons };
}

/** A failed check says the numbers are wrong, and no person's opinion can make them right. */
export function hasFailedChecks(reasons: readonly string[]): boolean {
  return reasons.some(
    (reason) =>
      reason === "schema_invalid" || reason === "payment_mismatch" || reason.startsWith("citation_failed:"),
  );
}
