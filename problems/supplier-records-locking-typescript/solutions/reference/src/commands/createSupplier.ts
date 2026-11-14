// POST /suppliers

import { readJsonObject } from "../kernel/body.ts";
import { ApiError, validationFailed } from "../kernel/errors.ts";
import type { FieldProblem } from "../kernel/errors.ts";
import type { RouteRequest, Answer } from "../kernel/router.ts";
import { requestIdProblems } from "../kernel/versionCheck.ts";
import { pickEditable, validateAllFields } from "../model/supplier.ts";
import type { SupplierStore } from "../model/supplierStore.ts";

const ID_FORMAT = /^S-\d+$/;

export function createSupplier(store: SupplierStore): (request: RouteRequest) => Answer {
  return (request) => {
    const input = readJsonObject(request.body);
    const id = input.id;
    const problems: FieldProblem[] = [];
    if (typeof id !== "string" || !ID_FORMAT.test(id)) {
      problems.push({ field: "id", message: "must look like S-123" });
    }
    problems.push(...validateAllFields(input), ...requestIdProblems(input));
    if (problems.length > 0) {
      throw validationFailed(problems);
    }
    if (store.find(id as string) !== undefined) {
      throw new ApiError(409, "already_exists", `Supplier ${id as string} already exists`);
    }
    return { status: 201, body: store.create(id as string, pickEditable(input)) };
  };
}
