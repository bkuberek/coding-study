// The handlers for /loans.

import type { ConditionStore } from "../data/conditionStore.ts";
import { selectPage } from "../data/listing.ts";
import type { LoanStore } from "../data/loanStore.ts";
import { canMove, needsClearedConditions } from "../domain/stages.ts";
import { conditionsOpen, illegalTransition, notFound } from "../errors.ts";
import type { Router } from "../http/router.ts";
import type { Loan } from "../types.ts";
import { parseListQuery } from "../validation/listQuery.ts";
import { parseNewLoan, parseStageMove } from "../validation/loans.ts";

/** The loan, or the 404 every route under /loans/:id answers. */
export function requireLoan(store: LoanStore, id: string): Loan {
  const loan = store.get(id);
  if (loan === undefined) {
    throw notFound(`No loan with id ${id}`);
  }
  return loan;
}

export function registerLoanRoutes(
  router: Router,
  loans: LoanStore,
  conditions: ConditionStore,
): void {
  router.add("GET", "/loans", (context) => {
    const query = parseListQuery(context.query);
    return { status: 200, body: selectPage(loans.list(), query) };
  });

  router.add("POST", "/loans", (context) => {
    return { status: 201, body: loans.insert(parseNewLoan(context.body)) };
  });

  router.add("GET", "/loans/:id", (context) => {
    return { status: 200, body: requireLoan(loans, context.params.id) };
  });

  router.add("POST", "/loans/:id/transition", (context) => {
    const loan = requireLoan(loans, context.params.id);
    const to = parseStageMove(context.body);
    if (!canMove(loan.stage, to)) {
      throw illegalTransition(loan.stage, to);
    }
    const open = conditions.openIds(loan.id);
    if (needsClearedConditions(to) && open.length > 0) {
      throw conditionsOpen(loan.id, open);
    }
    loan.stage = to;
    return { status: 200, body: loan };
  });
}
