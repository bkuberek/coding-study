// The service's entry point: wires the stores to the routes and answers one request at a time.

import { ConditionStore } from "./data/conditionStore.ts";
import { LoanStore } from "./data/loanStore.ts";
import { SEED_LOANS } from "./data/seed.ts";
import { ApiError } from "./errors.ts";
import { stableStringify } from "./http/json.ts";
import { Router } from "./http/router.ts";
import type { ApiResponse } from "./http/router.ts";
import { registerConditionRoutes } from "./routes/conditions.ts";
import { registerInternalRoutes } from "./routes/internal.ts";
import { registerLoanRoutes } from "./routes/loans.ts";

const INTERNAL_ERROR: ApiResponse = {
  status: 500,
  body: { error: { code: "internal_error", message: "Internal server error" } },
};

export class LoanApi {
  readonly #router = new Router();

  constructor() {
    const loans = new LoanStore(SEED_LOANS);
    const conditions = new ConditionStore();
    registerLoanRoutes(this.#router, loans, conditions);
    registerConditionRoutes(this.#router, loans, conditions);
    registerInternalRoutes(this.#router, loans);
  }

  /** `body` is the raw request text, "" for none. Returns `[status, json]`. */
  request(method: string, path: string, body: string): string[] {
    const response = this.#respond(method, path, body);
    return [String(response.status), stableStringify(response.body)];
  }

  #respond(method: string, path: string, body: string): ApiResponse {
    try {
      return this.#router.dispatch(method, path, body);
    } catch (error) {
      if (error instanceof ApiError) {
        return error.toResponse();
      }
      // The cause belongs in the service's logs, never in the answer to a client.
      console.error(error);
      return INTERNAL_ERROR;
    }
  }
}
