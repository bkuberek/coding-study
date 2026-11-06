// The handlers for /loans/:id/conditions: a child resource, always reached through its parent.

import type { ConditionStore } from "../data/conditionStore.ts";
import type { LoanStore } from "../data/loanStore.ts";
import { isTerminal } from "../domain/stages.ts";
import { loanClosed, notFound } from "../errors.ts";
import type { Router } from "../http/router.ts";
import { parseConditionText } from "../validation/loans.ts";
import { requireLoan } from "./loans.ts";

export function registerConditionRoutes(
  router: Router,
  loans: LoanStore,
  conditions: ConditionStore,
): void {
  router.add("POST", "/loans/:id/conditions", (context) => {
    const loan = requireLoan(loans, context.params.id);
    const text = parseConditionText(context.body);
    if (isTerminal(loan.stage)) {
      throw loanClosed(loan.id);
    }
    return { status: 201, body: conditions.add(loan.id, text) };
  });

  router.add("GET", "/loans/:id/conditions", (context) => {
    const loan = requireLoan(loans, context.params.id);
    const items = conditions.forLoan(loan.id);
    return { status: 200, body: { items, total: items.length } };
  });

  router.add("POST", "/loans/:id/conditions/:conditionId/clear", (context) => {
    const loan = requireLoan(loans, context.params.id);
    const { conditionId } = context.params;
    const condition = conditions.find(loan.id, conditionId);
    if (condition === undefined) {
      throw notFound(`No condition ${conditionId} on loan ${loan.id}`);
    }
    condition.status = "cleared";
    return { status: 200, body: condition };
  });
}
