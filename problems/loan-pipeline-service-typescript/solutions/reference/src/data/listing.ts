// The listing pipeline: filter, then sort, then cut a page. In a database these would be WHERE,
// ORDER BY and LIMIT, in that order, and for the same reasons.

import type { ListQuery, Loan, LoanPage, SortKey } from "../types.ts";

export function selectPage(loans: readonly Loan[], query: ListQuery): LoanPage {
  const matching = loans.filter((loan) => matches(loan, query));
  const ordered = matching.toSorted(byKeyThenId(query.sort, query.descending));
  const start = (query.page - 1) * query.pageSize;
  return {
    items: ordered.slice(start, start + query.pageSize),
    page: query.page,
    pageSize: query.pageSize,
    total: matching.length,
  };
}

function matches(loan: Loan, query: ListQuery): boolean {
  return (
    (query.stage === null || loan.stage === query.stage) &&
    loan.applicant.toLowerCase().includes(query.search) &&
    (query.minAmountCents === null || loan.amountCents >= query.minAmountCents) &&
    (query.maxAmountCents === null || loan.amountCents <= query.maxAmountCents)
  );
}

/** The direction applies to the key only: ties stay in id order, so paging never repeats a row. */
function byKeyThenId(key: SortKey, descending: boolean): (a: Loan, b: Loan) => number {
  return (a, b) => {
    const order = compare(a[key], b[key]);
    if (order !== 0) {
      return descending ? -order : order;
    }
    return compare(a.id, b.id);
  };
}

function compare<T extends string | number>(a: T, b: T): number {
  if (a < b) {
    return -1;
  }
  return a > b ? 1 : 0;
}
