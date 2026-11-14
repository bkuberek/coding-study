// The payment against values worked by hand, and the rounding rule on an exact half.

import assert from "node:assert/strict";
import { test } from "node:test";

import { readBps, readCents, readMonths } from "../src/checks/normalize.ts";
import { derive, monthlyPaymentCents } from "../src/money/loanMath.ts";

test("a known payment", () => {
  assert.equal(monthlyPaymentCents(1_250_000, 725, 36), 38739);
});

test("a zero rate divides, and a half goes up", () => {
  assert.equal(monthlyPaymentCents(120_000, 0, 12), 10_000);
  assert.equal(monthlyPaymentCents(25, 0, 2), 13);
  assert.equal(monthlyPaymentCents(10_000, 0, 3), 3333);
});

test("rounding can leave a charge a little below zero", () => {
  assert.equal(derive(10_000, 0, 3, 100_000, 3333).financeChargeCents, -1);
});

test("reading money from a form", () => {
  assert.equal(readCents("$12,500.00"), 1_250_000);
  assert.equal(readCents("12500"), 1_250_000);
  assert.equal(readCents("12,500.5"), 1_250_050);
  assert.equal(readCents("12,50.00"), null);
  assert.equal(readCents("12.345"), null);
  assert.equal(readCents("about 12500"), null);
});

test("reading a rate and a term", () => {
  assert.equal(readBps("7.25%"), 725);
  assert.equal(readBps("7.5"), 750);
  assert.equal(readBps("0%"), 0);
  assert.equal(readBps("7.255%"), null);
  assert.equal(readMonths("36 months"), 36);
  assert.equal(readMonths("1 month"), 1);
  assert.equal(readMonths("3 years"), null);
});
