// The model's output is untrusted input, like anything else from outside the program. This turns
// text into values that are exactly what the rest of the code expects, or into a list of errors.

import { FIELD_NAMES, VALUE_RULES } from "./extraction.ts";
import type { ExtractedValue, ExtractedValues } from "./extraction.ts";

export interface Validated {
  errors: string[];
  values: ExtractedValues | null;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function entryErrors(name: string, entry: unknown): string[] {
  const path = `values.${name}`;
  if (entry === undefined) {
    return [`${path}: is required`];
  }
  if (!isObject(entry)) {
    return [`${path}: must be an object`];
  }
  const errors: string[] = [];
  const rule = VALUE_RULES.get(name);
  if (rule !== undefined && !rule.check(entry.value)) {
    errors.push(`${path}.value: ${rule.message}`);
  }
  const { confidence, source } = entry;
  if (typeof confidence !== "number" || !Number.isFinite(confidence) || confidence < 0 || confidence > 1) {
    errors.push(`${path}.confidence: must be a number from 0 to 1`);
  }
  if (typeof source !== "string" || source === "") {
    errors.push(`${path}.source: must be non-empty text`);
  }
  return errors;
}

export function validateModelOutput(text: string): Validated {
  let output: unknown;
  try {
    output = JSON.parse(text);
  } catch {
    return { errors: ["modelOutput: not valid JSON"], values: null };
  }
  if (!isObject(output)) {
    return { errors: ["modelOutput: must be an object"], values: null };
  }
  const given = output.values;
  if (!isObject(given)) {
    return { errors: ["values: must be an object"], values: null };
  }
  const errors = FIELD_NAMES.flatMap((name) =>
    entryErrors(name, Object.hasOwn(given, name) ? given[name] : undefined),
  );
  if (errors.length > 0) {
    return { errors, values: null };
  }
  const values = Object.fromEntries(
    FIELD_NAMES.map((name) => {
      const { value, confidence, source } = given[name] as ExtractedValue;
      return [name, { by: "model", confidence, source, value }];
    }),
  ) as unknown as ExtractedValues;
  return { errors: [], values };
}
