// What the extraction step hands us for each field of a loan, and the rules for each.

export const FIELD_NAMES = [
  "applicantName",
  "amountCents",
  "rateBps",
  "termMonths",
  "monthlyIncomeCents",
  "statedPaymentCents",
] as const;

export type FieldName = (typeof FIELD_NAMES)[number];

export interface ExtractedValue {
  value: string | number;
  /** null once a person has supplied the value. */
  confidence: number | null;
  source: string;
  by: string;
}

export type ExtractedValues = Record<FieldName, ExtractedValue>;

const TEXT_MESSAGE = "must be non-empty text";

function whole(low: number, high: number): { check: (value: unknown) => boolean; message: string } {
  return {
    check: (value) => typeof value === "number" && Number.isInteger(value) && value >= low && value <= high,
    message: `must be a whole number from ${low} to ${high}`,
  };
}

export const VALUE_RULES: ReadonlyMap<string, { check: (value: unknown) => boolean; message: string }> = new Map([
  ["applicantName", { check: (value: unknown) => typeof value === "string" && value.trim() !== "", message: TEXT_MESSAGE }],
  ["amountCents", whole(1, 100_000_000)],
  ["rateBps", whole(0, 5000)],
  ["termMonths", whole(1, 480)],
  ["monthlyIncomeCents", whole(1, 100_000_000)],
  ["statedPaymentCents", whole(0, 100_000_000)],
]);
