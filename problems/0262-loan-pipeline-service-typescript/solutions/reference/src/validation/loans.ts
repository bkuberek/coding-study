// Validation of request bodies: every field is checked, so one answer lists every problem.

import { LOAN_DEFAULTS } from "../domain/loanDefaults.ts";
import { STAGES } from "../domain/stages.ts";
import { validationFailed } from "../errors.ts";
import type { FieldError } from "../errors.ts";
import { readJsonObject } from "../http/body.ts";
import type { NewLoan, Stage } from "../types.ts";

const MAX_AMOUNT_CENTS = 100_000_000;
const MIN_TERM_MONTHS = 6;
const MAX_TERM_MONTHS = 360;
const PURPOSES: readonly string[] = ["auto", "business", "education", "home", "unspecified"];
const DAY_FORMAT = /^\d{4}-\d{2}-\d{2}$/;

export function parseNewLoan(body: string): NewLoan {
  const input = readJsonObject(body);
  const errors: FieldError[] = [];
  const check = (field: string, valid: boolean, message: string): void => {
    if (!valid) {
      errors.push({ field, message });
    }
  };
  const { applicant, amountCents, appliedOn } = input;
  const termMonths = input.termMonths ?? LOAN_DEFAULTS.termMonths;
  const purpose = input.purpose ?? LOAN_DEFAULTS.purpose;
  const coApplicant = input.coApplicant ?? LOAN_DEFAULTS.coApplicant;
  check("applicant", isFilledText(applicant), "must be a non-empty string");
  check(
    "amountCents",
    isWholeNumberBetween(amountCents, 1, MAX_AMOUNT_CENTS),
    `must be a whole number from 1 to ${MAX_AMOUNT_CENTS}`,
  );
  check("appliedOn", isRealDay(appliedOn), "must be a real date as YYYY-MM-DD");
  check(
    "termMonths",
    isWholeNumberBetween(termMonths, MIN_TERM_MONTHS, MAX_TERM_MONTHS),
    `must be a whole number from ${MIN_TERM_MONTHS} to ${MAX_TERM_MONTHS}`,
  );
  check(
    "purpose",
    typeof purpose === "string" && PURPOSES.includes(purpose),
    `must be one of ${PURPOSES.join(", ")}`,
  );
  check(
    "coApplicant",
    coApplicant === null || isFilledText(coApplicant),
    "must be a non-empty string or null",
  );
  if (errors.length > 0) {
    throw validationFailed(errors);
  }
  return {
    applicant: (applicant as string).trim(),
    amountCents: amountCents as number,
    appliedOn: appliedOn as string,
    termMonths: termMonths as number,
    purpose: purpose as string,
    coApplicant: coApplicant === null ? null : (coApplicant as string).trim(),
  };
}

/** The stage a transition request asks for. */
export function parseStageMove(body: string): Stage {
  const { to } = readJsonObject(body);
  if (typeof to !== "string" || !(STAGES as readonly string[]).includes(to)) {
    const message = `must be one of ${STAGES.join(", ")}`;
    throw validationFailed([{ field: "to", message }]);
  }
  return to as Stage;
}

/** The trimmed text of a new condition. */
export function parseConditionText(body: string): string {
  const { text } = readJsonObject(body);
  if (!isFilledText(text)) {
    throw validationFailed([{ field: "text", message: "must be a non-empty string" }]);
  }
  return (text as string).trim();
}

function isFilledText(value: unknown): boolean {
  return typeof value === "string" && value.trim() !== "";
}

function isWholeNumberBetween(value: unknown, min: number, max: number): boolean {
  return Number.isInteger(value) && (value as number) >= min && (value as number) <= max;
}

/** `new Date("2026-02-30")` quietly becomes 2 March, so the parsed day must read back the same. */
function isRealDay(value: unknown): boolean {
  if (typeof value !== "string" || !DAY_FORMAT.test(value)) {
    return false;
  }
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().startsWith(value);
}
