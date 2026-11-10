// Checks a value against one of the tools' parameter schemas. They use only the keywords
// `JsonSchema` names, so this is all they mean, not a general JSON Schema validator.

import type { JsonSchema } from "./tools.ts";

type Fields = Record<string, unknown>;

function isFields(value: unknown): value is Fields {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function objectProblems(
  schema: Extract<JsonSchema, { type: "object" }>,
  value: unknown,
  where: string,
): string[] {
  if (!isFields(value)) {
    return [`${where}: expected an object`];
  }
  const missing = schema.required
    .filter((name) => !Object.hasOwn(value, name))
    .map((name) => `${where}.${name}: required`);
  const unknown = Object.keys(value)
    .filter((name) => !Object.hasOwn(schema.properties, name))
    .map((name) => `${where}.${name}: not a parameter`);
  const wrong = Object.entries(schema.properties)
    .filter(([name]) => Object.hasOwn(value, name))
    .flatMap(([name, property]) => problemsWith(property, value[name], `${where}.${name}`));
  return [...missing, ...unknown, ...wrong];
}

function stringProblems(
  schema: Extract<JsonSchema, { type: "string" }>,
  value: unknown,
  where: string,
): string[] {
  if (typeof value !== "string") {
    return [`${where}: expected a string`];
  }
  const characters = [...value].length;
  const problems: string[] = [];
  if (schema.minLength !== undefined && characters < schema.minLength) {
    problems.push(`${where}: at least ${schema.minLength} characters`);
  }
  if (schema.maxLength !== undefined && characters > schema.maxLength) {
    problems.push(`${where}: at most ${schema.maxLength} characters`);
  }
  if (schema.pattern !== undefined && !new RegExp(schema.pattern, "u").test(value)) {
    problems.push(`${where}: must match ${schema.pattern}`);
  }
  if (schema.enum !== undefined && !schema.enum.includes(value)) {
    problems.push(`${where}: one of ${schema.enum.join(", ")}`);
  }
  return problems;
}

function integerProblems(
  schema: Extract<JsonSchema, { type: "integer" }>,
  value: unknown,
  where: string,
): string[] {
  if (typeof value !== "number" || !Number.isInteger(value)) {
    return [`${where}: expected a whole number`];
  }
  const problems: string[] = [];
  if (schema.minimum !== undefined && value < schema.minimum) {
    problems.push(`${where}: at least ${schema.minimum}`);
  }
  if (schema.maximum !== undefined && value > schema.maximum) {
    problems.push(`${where}: at most ${schema.maximum}`);
  }
  return problems;
}

/** What is wrong with `value` for `schema`, each problem naming where it is; empty when it fits. */
export function problemsWith(schema: JsonSchema, value: unknown, where = "arguments"): string[] {
  switch (schema.type) {
    case "object":
      return objectProblems(schema, value, where);
    case "string":
      return stringProblems(schema, value, where);
    case "integer":
      return integerProblems(schema, value, where);
  }
}
