// The in-memory table of conditions: a child of loans, joined by `loanId`.

import type { Condition } from "../types.ts";

export class ConditionStore {
  readonly #conditions: Condition[] = [];
  #nextNumber = 1;

  add(loanId: string, text: string): Condition {
    const condition: Condition = { id: `C-${this.#nextNumber}`, loanId, text, status: "open" };
    this.#nextNumber += 1;
    this.#conditions.push(condition);
    return condition;
  }

  forLoan(loanId: string): Condition[] {
    return this.#conditions.filter((condition) => condition.loanId === loanId);
  }

  /** Scoped by loan: a condition is found only through the loan it belongs to. */
  find(loanId: string, id: string): Condition | undefined {
    return this.forLoan(loanId).find((condition) => condition.id === id);
  }

  openIds(loanId: string): string[] {
    return this.forLoan(loanId)
      .filter((condition) => condition.status === "open")
      .map((condition) => condition.id);
  }
}
