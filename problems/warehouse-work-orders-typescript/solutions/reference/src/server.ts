// The service: builds each feature and answers one request at a time.

import { ReplayCache } from "./idempotency/replayCache.ts";
import { partRoutes } from "./parts/routes.ts";
import { PartStore } from "./parts/store.ts";
import { reportRoutes } from "./reports/routes.ts";
import { dispatch } from "./shared/routing.ts";
import type { Answer, Route } from "./shared/routing.ts";
import { canonicalJson } from "./shared/json.ts";
import { HttpProblem } from "./shared/problems.ts";
import { siteRoutes } from "./sites/routes.ts";
import { SEED_SITES, SiteDirectory } from "./sites/directory.ts";
import { workOrderRoutes } from "./workorders/routes.ts";
import { SEED_WORK_ORDERS, WorkOrderStore } from "./workorders/store.ts";

const INTERNAL_ERROR: Answer = {
  status: 500,
  body: { error: { code: "internal_error", message: "Internal server error" } },
};

export class WorkOrderApi {
  readonly #routes: readonly Route[];

  constructor() {
    const sites = new SiteDirectory(SEED_SITES);
    const orders = new WorkOrderStore(SEED_WORK_ORDERS);
    const parts = new PartStore();
    const features = { orders, sites, parts };
    this.#routes = [
      ...siteRoutes(sites),
      ...workOrderRoutes(features, new ReplayCache()),
      ...partRoutes(features),
      ...reportRoutes(features),
    ];
  }

  /** `headers` holds `"Name: value"` strings; `body` is the raw request text, "" for none. */
  request(method: string, path: string, headers: string[], body: string): string[] {
    const answer = this.#answer(method, path, headers, body);
    return [String(answer.status), canonicalJson(answer.body)];
  }

  #answer(method: string, path: string, headers: string[], body: string): Answer {
    try {
      return dispatch(this.#routes, { method, path, headers, body });
    } catch (thrown) {
      if (thrown instanceof HttpProblem) {
        return thrown.toAnswer();
      }
      console.error(thrown);
      return INTERNAL_ERROR;
    }
  }
}
