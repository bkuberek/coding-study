// The listing pipeline on its own: the order of its steps is what these pin down.

import assert from "node:assert/strict";
import { test } from "node:test";

import { selectPage } from "../src/data/listing.ts";
import { LOAN_DEFAULTS } from "../src/domain/loanDefaults.ts";
import type { ListQuery, Loan } from "../src/types.ts";

function loan(id: string, amountCents: number): Loan {
  const base = { applicant: id, appliedOn: "2026-01-01", stage: "submitted" as const };
  return { id, amountCents, ...base, ...LOAN_DEFAULTS };
}

const ALL: ListQuery = {
  stage: null,
  search: "",
  minAmountCents: null,
  maxAmountCents: null,
  sort: "id",
  descending: false,
  page: 1,
  pageSize: 20,
};

test("ties stay in id order in both directions", () => {
  const loans = [loan("a", 5), loan("b", 9), loan("c", 5)];
  const page = selectPage(loans, { ...ALL, sort: "amountCents", descending: true });
  assert.deepEqual(page.items.map((item) => item.id), ["b", "a", "c"]);
});

test("the total counts the matches, not the page", () => {
  const loans = [loan("a", 5), loan("b", 9), loan("c", 500)];
  const page = selectPage(loans, { ...ALL, maxAmountCents: 9, pageSize: 1 });
  assert.deepEqual(page.items.map((item) => item.id), ["a"]);
  assert.equal(page.total, 2);
});

test("selecting a page leaves the table's order alone", () => {
  const loans = [loan("a", 5), loan("b", 9)];
  selectPage(loans, { ...ALL, sort: "amountCents", descending: true });
  assert.deepEqual(loans.map((item) => item.id), ["a", "b"]);
});
