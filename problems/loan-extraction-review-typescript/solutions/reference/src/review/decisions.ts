// What a person may do to a case. The model proposes and code validates, and only here does anybody
// decide. Every attempt leaves a line in the audit trail, including those that are refused.

import { checkCitation } from "../checks/citations.ts";
import type { ReviewCase } from "../cases/caseStore.ts";
import { FIELD_NAMES, VALUE_RULES } from "../intake/extraction.ts";
import type { FieldName } from "../intake/extraction.ts";
import { assess, hasFailedChecks } from "./assessment.ts";

const WHOLE_DIGITS = /^\d+$/;

export function writeAudit(reviewCase: ReviewCase, line: string): void {
  reviewCase.audit.push(`${reviewCase.audit.length + 1} ${line}`);
}

function isBlank(text: string): boolean {
  return text.trim() === "";
}

function actorOf(reviewer: string): string {
  return isBlank(reviewer) ? "unknown" : reviewer;
}

function refusalOfDecision(reviewCase: ReviewCase, reviewer: string, decision: string, note: string): string | null {
  if (isBlank(reviewer)) {
    return "reviewer_required";
  }
  if (decision !== "approve" && decision !== "decline") {
    return "bad_decision";
  }
  if (isBlank(note)) {
    return "note_required";
  }
  if (reviewCase.state !== "awaiting_person") {
    return "not_awaiting_review";
  }
  if (decision === "approve" && hasFailedChecks(reviewCase.reasons)) {
    return "checks_failing";
  }
  return null;
}

export function decide(reviewCase: ReviewCase, reviewer: string, decision: string, note: string): string {
  const refusal = refusalOfDecision(reviewCase, reviewer, decision, note);
  if (refusal !== null) {
    writeAudit(reviewCase, `${actorOf(reviewer)} refused ${decision}: ${refusal}`);
    return `refused:${refusal}`;
  }
  reviewCase.state = decision === "approve" ? "approved_by_person" : "declined_by_person";
  writeAudit(reviewCase, `${reviewer} ${decision}: ${note}`);
  return "recorded";
}

function isField(name: string): name is FieldName {
  return (FIELD_NAMES as readonly string[]).includes(name);
}

/** The text a person typed, as the field's type, or undefined when it cannot be one. */
function parsedValue(field: FieldName, text: string): string | number | undefined {
  const value = field === "applicantName" ? text : WHOLE_DIGITS.test(text) ? Number(text) : undefined;
  return VALUE_RULES.get(field)?.check(value) ? value : undefined;
}

function refusalOfCorrection(
  reviewCase: ReviewCase,
  reviewer: string,
  field: string,
  text: string,
  source: string,
): string | null {
  if (isBlank(reviewer)) {
    return "reviewer_required";
  }
  if (reviewCase.state !== "awaiting_person") {
    return "not_awaiting_review";
  }
  if (reviewCase.values === null) {
    return "nothing_to_correct";
  }
  if (!isField(field)) {
    return "unknown_field";
  }
  const value = parsedValue(field, text);
  if (value === undefined) {
    return "invalid_value";
  }
  return checkCitation(reviewCase.document, field, value, source) === "ok" ? null : "citation_failed";
}

export function correct(reviewCase: ReviewCase, reviewer: string, field: string, text: string, source: string): string {
  const refusal = refusalOfCorrection(reviewCase, reviewer, field, text, source);
  if (refusal !== null) {
    writeAudit(reviewCase, `${actorOf(reviewer)} refused correct ${field}: ${refusal}`);
    return `refused:${refusal}`;
  }
  const values = reviewCase.values;
  if (values === null || !isField(field)) {
    return "refused:nothing_to_correct";
  }
  const value = parsedValue(field, text) ?? text;
  const before = values[field].value;
  values[field] = { by: reviewer, confidence: null, source, value };
  reviewCase.assessment = assess(reviewCase.document, values);
  reviewCase.reasons = reviewCase.assessment.reasons;
  reviewCase.autoApprovable = false;
  writeAudit(reviewCase, `${reviewer} corrected ${field}: ${before} -> ${value} from ${source}`);
  writeAudit(reviewCase, routeLine(reviewCase.reasons, false));
  return "recorded";
}

export function routeLine(reasons: readonly string[], autoApprove: boolean): string {
  if (autoApprove) {
    return "system routed auto_approve";
  }
  return reasons.length === 0 ? "system routed person" : `system routed person ${reasons.join(",")}`;
}
