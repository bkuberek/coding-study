// A test seam: lets a test simulate a store outage through the API, since every test talks to the
// service through `request`. A real deployment would not expose these routes.

import type { LoanStore } from "../data/loanStore.ts";
import type { Router } from "../http/router.ts";

export function registerInternalRoutes(router: Router, store: LoanStore): void {
  router.add("POST", "/internal/store-outage", (context) => {
    const { reason } = JSON.parse(context.body) as { reason: string };
    store.setOutage(reason);
    return { status: 200, body: { outage: true } };
  });

  router.add("DELETE", "/internal/store-outage", () => {
    store.setOutage(null);
    return { status: 200, body: { outage: false } };
  });
}
