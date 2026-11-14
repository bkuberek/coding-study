// The rows the store starts with. The people are made up, and so are the amounts.

import type { Loan } from "../types.ts";

export const SEED_LOANS: readonly Loan[] = [
  { id: "L-1001", applicant: "Ada Placeholder", amountCents: 1250000, appliedOn: "2026-01-12", stage: "review" },
  { id: "L-1002", applicant: "Ben Sampleton", amountCents: 480000, appliedOn: "2026-02-03", stage: "submitted" },
  { id: "L-1003", applicant: "Cy Fictitious", amountCents: 9900000, appliedOn: "2026-02-20", stage: "approved" },
  { id: "L-1004", applicant: "Dee Testcase", amountCents: 75000, appliedOn: "2026-03-01", stage: "funded" },
];
