// The service's data types.

export type Stage = "submitted" | "review" | "approved" | "declined" | "funded" | "withdrawn";

/** One loan application, as the API returns it. */
export interface Loan {
  readonly id: string;
  applicant: string;
  amountCents: number;
  appliedOn: string;
  stage: Stage;
  termMonths: number;
  purpose: string;
  coApplicant: string | null;
}

/** A validated request to open an application, with its defaults applied. */
export interface NewLoan {
  readonly applicant: string;
  readonly amountCents: number;
  readonly appliedOn: string;
  readonly termMonths: number;
  readonly purpose: string;
  readonly coApplicant: string | null;
}

export type SortKey = "amountCents" | "applicant" | "appliedOn" | "id" | "termMonths";

/** A validated `GET /loans` query: numbers are numbers here, and every default is applied. */
export interface ListQuery {
  readonly stage: Stage | null;
  readonly search: string;
  readonly minAmountCents: number | null;
  readonly maxAmountCents: number | null;
  readonly sort: SortKey;
  readonly descending: boolean;
  readonly page: number;
  readonly pageSize: number;
}

export interface LoanPage {
  readonly items: readonly Loan[];
  readonly page: number;
  readonly pageSize: number;
  readonly total: number;
}

export interface Condition {
  readonly id: string;
  readonly loanId: string;
  readonly text: string;
  status: "open" | "cleared";
}
