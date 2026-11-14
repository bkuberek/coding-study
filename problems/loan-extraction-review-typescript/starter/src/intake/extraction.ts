// What the extraction step hands us for each field of a loan.

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
  confidence: number;
  source: string;
}

export type ExtractedValues = Record<FieldName, ExtractedValue>;
