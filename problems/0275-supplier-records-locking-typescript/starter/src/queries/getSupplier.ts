// GET /suppliers/:id

import { notFound } from "../kernel/errors.ts";
import type { RouteRequest, Answer } from "../kernel/router.ts";
import type { SupplierStore } from "../model/supplierStore.ts";

export function getSupplier(store: SupplierStore): (request: RouteRequest) => Answer {
  return (request) => {
    const id = request.params.id ?? "";
    const supplier = store.find(id);
    if (supplier === undefined) {
      throw notFound(`supplier with id ${id}`);
    }
    return { status: 200, body: supplier };
  };
}
