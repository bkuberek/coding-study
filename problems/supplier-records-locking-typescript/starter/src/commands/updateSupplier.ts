// PUT /suppliers/:id

import { readJsonObject } from "../kernel/body.ts";
import { notFound, validationFailed } from "../kernel/errors.ts";
import type { RouteRequest, Answer } from "../kernel/router.ts";
import { pickEditable, validateAllFields } from "../model/supplier.ts";
import type { SupplierStore } from "../model/supplierStore.ts";

export function updateSupplier(store: SupplierStore): (request: RouteRequest) => Answer {
  return (request) => {
    const id = request.params.id ?? "";
    const current = store.find(id);
    if (current === undefined) {
      throw notFound(`supplier with id ${id}`);
    }
    const input = readJsonObject(request.body);
    const problems = validateAllFields(input);
    if (problems.length > 0) {
      throw validationFailed(problems);
    }
    return { status: 200, body: store.update(current, pickEditable(input)) };
  };
}
