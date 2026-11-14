// PATCH /suppliers/:id

import { readJsonObject } from "../kernel/body.ts";
import { ApiError, notFound, validationFailed } from "../kernel/errors.ts";
import type { FieldProblem } from "../kernel/errors.ts";
import type { RouteRequest, Answer } from "../kernel/router.ts";
import { requestIdProblems, requireVersionKey, versionProblems } from "../kernel/versionCheck.ts";
import { decideMerge } from "../model/merge.ts";
import { BELOW_MINIMUM, EDITABLE_FIELDS, problemWith } from "../model/supplier.ts";
import type { EditableField, EditableFields } from "../model/supplier.ts";
import type { SupplierStore } from "../model/supplierStore.ts";

function isEditable(key: string): key is EditableField {
  return (EDITABLE_FIELDS as readonly string[]).includes(key);
}

function changesProblems(changes: unknown): FieldProblem[] {
  if (changes === null || typeof changes !== "object" || Array.isArray(changes)) {
    return [{ field: "changes", message: "must be an object with at least one field" }];
  }
  const keys = Object.keys(changes).sort();
  if (keys.length === 0) {
    return [{ field: "changes", message: "must be an object with at least one field" }];
  }
  const problems: FieldProblem[] = [];
  for (const key of keys) {
    const message = isEditable(key)
      ? problemWith(key, (changes as Record<string, unknown>)[key])
      : "is not a field you can change";
    if (message !== null) {
      problems.push({ field: `changes.${key}`, message });
    }
  }
  return problems;
}

export function patchSupplier(store: SupplierStore): (request: RouteRequest) => Answer {
  return (request) => {
    const id = request.params.id ?? "";
    const current = store.find(id);
    if (current === undefined) {
      throw notFound(`supplier with id ${id}`);
    }
    const input = readJsonObject(request.body);
    requireVersionKey(input, "baseVersion");
    const problems = [
      ...versionProblems(input, "baseVersion"),
      ...changesProblems(input.changes),
      ...requestIdProblems(input),
    ];
    if (problems.length > 0) {
      throw validationFailed(problems);
    }

    const changes = input.changes as Partial<EditableFields>;
    const decision = decideMerge(current, input.baseVersion as number, changes, (field) =>
      store.lastChanged(id, field),
    );
    switch (decision.kind) {
      case "nothing":
        return { status: 200, body: current };
      case "invalid":
        throw validationFailed([BELOW_MINIMUM]);
      case "conflict":
        throw new ApiError(409, "merge_conflict", `Supplier ${id} changed underneath this edit`, {
          conflicts: decision.conflicts,
          current,
          currentVersion: current.version,
        });
      case "apply":
        return { status: 200, body: store.apply(current, changes) };
    }
  };
}
