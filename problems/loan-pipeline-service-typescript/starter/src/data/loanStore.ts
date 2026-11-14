// The in-memory table of loans. Everything above it treats this as the database.

import type { Loan, NewLoan } from "../types.ts";

const FIRST_LOAN_NUMBER = 1001;

export class LoanStore {
  readonly #loans: Loan[];
  #nextNumber: number;
  #outage: string | null = null;

  constructor(seed: readonly Loan[]) {
    this.#loans = seed.map((loan) => ({ ...loan }));
    this.#nextNumber = FIRST_LOAN_NUMBER + seed.length;
  }

  /** While an outage is set, every read and write throws, as a lost connection would. */
  setOutage(reason: string | null): void {
    this.#outage = reason;
  }

  list(): Loan[] {
    this.#checkAvailable();
    return this.#loans;
  }

  count(): number {
    this.#checkAvailable();
    return this.#loans.length;
  }

  get(id: string): Loan | undefined {
    this.#checkAvailable();
    return this.#loans.find((loan) => loan.id === id);
  }

  insert(input: NewLoan): Loan {
    this.#checkAvailable();
    const loan: Loan = {
      id: `L-${this.#nextNumber}`,
      applicant: input.applicant,
      amountCents: input.amountCents,
      appliedOn: input.appliedOn,
      stage: "submitted",
    };
    this.#nextNumber += 1;
    this.#loans.push(loan);
    return loan;
  }

  #checkAvailable(): void {
    if (this.#outage !== null) {
      throw new Error(this.#outage);
    }
  }
}
