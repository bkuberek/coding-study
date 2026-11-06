// Money on its own: the rounding rules, without going through a request.

import assert from "node:assert/strict";
import { test } from "node:test";

import { dividedHalfUp, orderCost } from "../src/parts/cost.ts";

const SITE = { id: "s", name: "s", laborRateCentsPerHour: 5130, partsMarkupBasisPoints: 250 };

test("a half rounds up, and integer arithmetic sees an exact half", () => {
  assert.equal(dividedHalfUp(5, 2), 3);
  assert.equal(dividedHalfUp(4, 2), 2);
  assert.equal(dividedHalfUp(7, 3), 2);
  assert.equal(dividedHalfUp(11 * 5130, 60), 941);
});

test("the markup rounds once, on the subtotal", () => {
  const line = { workOrderId: "w", lineNumber: 1, sku: "x", quantity: 1, unitCostCents: 60 };
  const cost = orderCost({ laborMinutes: 0 }, [line, { ...line, lineNumber: 2 }], SITE);
  assert.equal(cost.partsCostCents, 123);
});
