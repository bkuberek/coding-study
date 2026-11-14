// Whether the document says what the model says it says. A citation that does not check out is not
// a citation.

import type { SourceDocument } from "../intake/document.ts";
import { FIELD_NAMES } from "../intake/extraction.ts";
import type { ExtractedValues, FieldName } from "../intake/extraction.ts";
import { readBps, readCents, readMonths, sameText } from "./normalize.ts";

export type CitationResult = "ok" | "mismatch" | "missing_source";

const READERS: Record<Exclude<FieldName, "applicantName">, (text: string) => number | null> = {
  amountCents: readCents,
  rateBps: readBps,
  termMonths: readMonths,
  monthlyIncomeCents: readCents,
  statedPaymentCents: readCents,
};

export function checkCitation(
  document: SourceDocument,
  field: FieldName,
  value: string | number,
  source: string,
): CitationResult {
  if (!Object.hasOwn(document.fields, source)) {
    return "missing_source";
  }
  const text = document.fields[source] ?? "";
  if (field === "applicantName") {
    return sameText(String(value), text) ? "ok" : "mismatch";
  }
  return READERS[field](text) === value ? "ok" : "mismatch";
}

export function citationsOf(document: SourceDocument, values: ExtractedValues): Map<FieldName, CitationResult> {
  return new Map(
    FIELD_NAMES.map((field) => {
      const { value, source } = values[field];
      return [field, checkCitation(document, field, value, source)];
    }),
  );
}
