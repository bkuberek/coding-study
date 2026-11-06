// The service's data types.

export type Stage = "submitted" | "review" | "approved" | "declined" | "funded" | "withdrawn";

/** One loan application, as the API returns it. */
export interface Loan {
  readonly id: string;
  applicant: string;
  amountCents: number;
  appliedOn: string;
  stage: Stage;
}

/** What a client sends to open an application. */
export interface NewLoan {
  readonly applicant: string;
  readonly amountCents: number;
  readonly appliedOn: string;
}
