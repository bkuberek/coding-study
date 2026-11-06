// The service's entry point: wires the store to the routes and answers one request at a time.

import { LoanStore } from "./data/loanStore.ts";
import { SEED_LOANS } from "./data/seed.ts";
import { ApiError } from "./errors.ts";
import { stableStringify } from "./http/json.ts";
import { Router } from "./http/router.ts";
import type { ApiResponse } from "./http/router.ts";
import { registerInternalRoutes } from "./routes/internal.ts";
import { registerLoanRoutes } from "./routes/loans.ts";

export class LoanApi {
  readonly #router = new Router();

  constructor() {
    const store = new LoanStore(SEED_LOANS);
    registerLoanRoutes(this.#router, store);
    registerInternalRoutes(this.#router, store);
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
      throw error;
    }
  }
}
