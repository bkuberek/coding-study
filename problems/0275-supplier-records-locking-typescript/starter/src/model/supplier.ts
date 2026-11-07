// A supplier: its fields, and what each may hold.

import type { FieldProblem } from "../kernel/errors.ts";

export interface EditableFields {
  name: string;
  contactEmail: string;
  notes: string;
  minOrderCents: number;
  maxOrderCents: number;
  status: string;
}

export interface Supplier extends EditableFields {
  id: string;
  version: number;
}

export type EditableField = keyof EditableFields;

/** In the order a request's problems are reported. */
export const EDITABLE_FIELDS: readonly EditableField[] = [
  "name",
  "contactEmail",
  "notes",
  "minOrderCents",
  "maxOrderCents",
  "status",
];

function isWholeFromZero(value: unknown): boolean {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

const RULES: Record<EditableField, { check: (value: unknown) => boolean; message: string }> = {
  name: {
    check: (value) => typeof value === "string" && value.trim() !== "",
    message: "must be a non-empty string",
  },
  contactEmail: {
    check: (value) => typeof value === "string" && value.includes("@"),
    message: "must contain @",
  },
  notes: { check: (value) => typeof value === "string", message: "must be a string" },
  minOrderCents: { check: isWholeFromZero, message: "must be a whole number from 0" },
  maxOrderCents: { check: isWholeFromZero, message: "must be a whole number from 0" },
  status: {
    check: (value) => value === "active" || value === "paused",
    message: "must be active or paused",
  },
};

/** The problem with one field's value, or null. */
export function problemWith(field: EditableField, value: unknown): string | null {
  return RULES[field].check(value) ? null : RULES[field].message;
}

/** Every problem with a complete set of fields, in table order. */
export function validateAllFields(input: Record<string, unknown>): FieldProblem[] {
  const problems: FieldProblem[] = [];
  for (const field of EDITABLE_FIELDS) {
    const message = problemWith(field, input[field]);
    if (message !== null) {
      problems.push({ field, message });
    }
  }
  if (problems.length === 0 && isBelowMinimum(input)) {
    problems.push(BELOW_MINIMUM);
  }
  return problems;
}

export const BELOW_MINIMUM: FieldProblem = {
  field: "maxOrderCents",
  message: "must not be below minOrderCents",
};

export function isBelowMinimum(fields: Record<string, unknown>): boolean {
  return (fields.maxOrderCents as number) < (fields.minOrderCents as number);
}

export function pickEditable(input: Record<string, unknown>): EditableFields {
  return {
    name: input.name as string,
    contactEmail: input.contactEmail as string,
    notes: input.notes as string,
    minOrderCents: input.minOrderCents as number,
    maxOrderCents: input.maxOrderCents as number,
    status: input.status as string,
  };
}
