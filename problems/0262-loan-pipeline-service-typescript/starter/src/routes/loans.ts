// The handlers for /loans.

import type { LoanStore } from "../data/loanStore.ts";
import { notFound } from "../errors.ts";
import type { Router } from "../http/router.ts";
import type { NewLoan } from "../types.ts";

const DEFAULT_PAGE_SIZE = 20;

export function registerLoanRoutes(router: Router, store: LoanStore): void {
  router.add("GET", "/loans", () => {
    const body = { items: store.list(), page: 1, pageSize: DEFAULT_PAGE_SIZE, total: store.count() };
    return { status: 200, body };
  });

  router.add("POST", "/loans", (context) => {
    const input = JSON.parse(context.body) as NewLoan;
    return { status: 201, body: store.insert(input) };
  });

  router.add("GET", "/loans/:id", (context) => {
    const loan = store.get(context.params.id);
    if (loan === undefined) {
      throw notFound(`No loan with id ${context.params.id}`);
    }
    return { status: 200, body: loan };
  });
}
