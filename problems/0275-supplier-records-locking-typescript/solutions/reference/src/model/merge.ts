// Whether a change made against an old version can still go in. Pure, so that every path through it
// can be tested without a request.

import { isBelowMinimum } from "./supplier.ts";
import type { EditableField, EditableFields, Supplier } from "./supplier.ts";

export type MergeDecision =
  | { kind: "nothing" }
  | { kind: "apply" }
  | { kind: "invalid" }
  | { kind: "conflict"; conflicts: string[] };

/** `status` is a decision made about the whole record, so it never merges. */
const NEVER_MERGES: EditableField = "status";

export function decideMerge(
  current: Supplier,
  baseVersion: number,
  changes: Partial<EditableFields>,
  lastChanged: (field: EditableField) => number,
): MergeDecision {
  const changed = (Object.keys(changes) as EditableField[]).filter(
    (field) => changes[field] !== current[field],
  );
  if (changed.length === 0) {
    return { kind: "nothing" };
  }
  const merged = { ...current, ...changes };
  if (baseVersion === current.version) {
    return isBelowMinimum(merged) ? { kind: "invalid" } : { kind: "apply" };
  }
  const conflicts =
    baseVersion > current.version
      ? changed
      : changed.filter((field) => field === NEVER_MERGES || lastChanged(field) > baseVersion);
  if (conflicts.length > 0) {
    return { kind: "conflict", conflicts: [...conflicts].sort() };
  }
  if (isBelowMinimum(merged)) {
    return { kind: "conflict", conflicts: ["maxOrderCents", "minOrderCents"] };
  }
  return { kind: "apply" };
}
