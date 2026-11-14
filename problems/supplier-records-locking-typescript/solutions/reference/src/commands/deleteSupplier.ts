// DELETE /suppliers/:id. A delete is a write, so it says which version it read.

import { readJsonObject } from "../kernel/body.ts";
import { notFound, validationFailed } from "../kernel/errors.ts";
import type { RouteRequest, Answer } from "../kernel/router.ts";
import { requestIdProblems, requireVersionKey, staleWrite, versionProblems } from "../kernel/versionCheck.ts";
import type { SupplierStore } from "../model/supplierStore.ts";

export function deleteSupplier(store: SupplierStore): (request: RouteRequest) => Answer {
  return (request) => {
    const id = request.params.id ?? "";
    const current = store.find(id);
    if (current === undefined) {
      throw notFound(`supplier with id ${id}`);
    }
    const input = readJsonObject(request.body);
    requireVersionKey(input, "expectedVersion");
    const problems = [...versionProblems(input, "expectedVersion"), ...requestIdProblems(input)];
    if (problems.length > 0) {
      throw validationFailed(problems);
    }
    if (input.expectedVersion !== current.version) {
      throw staleWrite(`Supplier ${id}`, current);
    }
    return { status: 200, body: { deleted: true, id, version: store.delete(current) } };
  };
}
