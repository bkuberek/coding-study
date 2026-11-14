// GET /suppliers

import type { RouteRequest, Answer } from "../kernel/router.ts";
import type { SupplierStore } from "../model/supplierStore.ts";

export function listSuppliers(store: SupplierStore): (request: RouteRequest) => Answer {
  return () => ({ status: 200, body: { items: store.all() } });
}
