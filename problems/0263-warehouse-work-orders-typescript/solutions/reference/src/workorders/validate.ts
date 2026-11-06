// Validation of work order requests. Each field has one rule, and one request reports them all.

import { validationFailed } from "../shared/problems.ts";
import type { FieldProblem } from "../shared/problems.ts";
import type { SiteDirectory } from "../sites/directory.ts";
import type { NewWorkOrder, Priority, WorkOrderChanges } from "./model.ts";

const PRIORITIES: readonly unknown[] = ["low", "normal", "high"];
const MAX_LABOR_MINUTES = 100000;
const CREATE_FIELDS = new Set(["title", "siteId", "priority", "assignee", "laborMinutes"]);
const CHANGEABLE_FIELDS = new Set(["title", "priority", "assignee", "laborMinutes"]);

export const MESSAGES = {
  title: "must be a non-empty string",
  priority: "must be low, normal or high",
  assignee: "must be a non-empty string or null",
  laborMinutes: `must be a whole number from 0 to ${MAX_LABOR_MINUTES}`,
  siteId: "must be a known site id",
  unknownField: "is not a known field",
  cannotChange: "cannot be changed",
};

export function isFilledText(value: unknown): boolean {
  return typeof value === "string" && value.trim() !== "";
}

export function isPriority(value: unknown): boolean {
  return PRIORITIES.includes(value);
}

export function isLaborMinutes(value: unknown): boolean {
  return Number.isInteger(value) && (value as number) >= 0 && (value as number) <= MAX_LABOR_MINUTES;
}

export function parseNewWorkOrder(
  input: Readonly<Record<string, unknown>>,
  sites: SiteDirectory,
): NewWorkOrder {
  const { title, siteId } = input;
  const priority = input.priority ?? "normal";
  const assignee = input.assignee ?? null;
  const laborMinutes = input.laborMinutes ?? 0;
  const problems: FieldProblem[] = [];
  if (!isFilledText(title)) {
    problems.push({ field: "title", message: MESSAGES.title });
  }
  if (typeof siteId !== "string" || sites.get(siteId) === undefined) {
    problems.push({ field: "siteId", message: MESSAGES.siteId });
  }
  if (!isPriority(priority)) {
    problems.push({ field: "priority", message: MESSAGES.priority });
  }
  if (assignee !== null && !isFilledText(assignee)) {
    problems.push({ field: "assignee", message: MESSAGES.assignee });
  }
  if (!isLaborMinutes(laborMinutes)) {
    problems.push({ field: "laborMinutes", message: MESSAGES.laborMinutes });
  }
  for (const key of Object.keys(input).sort()) {
    if (!CREATE_FIELDS.has(key)) {
      problems.push({ field: key, message: MESSAGES.unknownField });
    }
  }
  if (problems.length > 0) {
    throw validationFailed(problems);
  }
  return {
    title: (title as string).trim(),
    siteId: siteId as string,
    priority: priority as Priority,
    assignee: assignee === null ? null : (assignee as string).trim(),
    laborMinutes: laborMinutes as number,
  };
}

/**
 * A partial update, where a missing key and a null are different requests: `"key" in input` asks
 * whether the client sent it, and only then does its value matter. Only `assignee` may be null.
 */
export function parseChanges(input: Readonly<Record<string, unknown>>): WorkOrderChanges {
  const problems: FieldProblem[] = [];
  const check = (field: string, valid: (value: unknown) => boolean, message: string): void => {
    if (field in input && !valid(input[field])) {
      problems.push({ field, message });
    }
  };
  check("title", isFilledText, MESSAGES.title);
  check("priority", isPriority, MESSAGES.priority);
  check("assignee", (value) => value === null || isFilledText(value), MESSAGES.assignee);
  check("laborMinutes", isLaborMinutes, MESSAGES.laborMinutes);
  for (const key of Object.keys(input).sort()) {
    if (!CHANGEABLE_FIELDS.has(key)) {
      problems.push({ field: key, message: MESSAGES.cannotChange });
    }
  }
  if (problems.length > 0) {
    throw validationFailed(problems);
  }
  const changes: Record<string, unknown> = { ...input };
  if (typeof input.title === "string") {
    changes.title = input.title.trim();
  }
  if (typeof input.assignee === "string") {
    changes.assignee = input.assignee.trim();
  }
  return changes as WorkOrderChanges;
}
