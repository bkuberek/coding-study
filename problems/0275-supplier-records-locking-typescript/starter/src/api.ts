// The service: lists its routes, and turns every outcome into a status and a JSON body.

import { createSupplier } from "./commands/createSupplier.ts";
import { updateSupplier } from "./commands/updateSupplier.ts";
import { ApiError } from "./kernel/errors.ts";
import { canonicalJson } from "./kernel/json.ts";
import { dispatch } from "./kernel/router.ts";
import type { Answer, Route } from "./kernel/router.ts";
import { SEED_SUPPLIERS, SupplierStore } from "./model/supplierStore.ts";
import { getSupplier } from "./queries/getSupplier.ts";
import { listSuppliers } from "./queries/listSuppliers.ts";

const INTERNAL_ERROR: Answer = {
  status: 500,
  body: { error: { code: "internal_error", message: "Internal server error" } },
};

export class SupplierApi {
  readonly #routes: readonly Route[];

  constructor() {
    const suppliers = new SupplierStore(SEED_SUPPLIERS);
    this.#routes = [
      { method: "GET", pattern: "/suppliers", handle: listSuppliers(suppliers) },
      { method: "POST", pattern: "/suppliers", handle: createSupplier(suppliers) },
      { method: "GET", pattern: "/suppliers/:id", handle: getSupplier(suppliers) },
      { method: "PUT", pattern: "/suppliers/:id", handle: updateSupplier(suppliers) },
    ];
  }

  /** `body` is the raw request text, "" for none. Answers `[status, json]`. */
  request(method: string, path: string, body: string): string[] {
    const answer = this.#answer(method, path, body);
    return [String(answer.status), canonicalJson(answer.body)];
  }

  #answer(method: string, path: string, body: string): Answer {
    try {
      return dispatch(this.#routes, { method, path, body });
    } catch (thrown) {
      if (thrown instanceof ApiError) {
        return { status: thrown.status, body: thrown.body() };
      }
      console.error(thrown);
      return INTERNAL_ERROR;
    }
  }
}
