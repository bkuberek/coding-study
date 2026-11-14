import assert from "node:assert/strict";
import { test } from "node:test";

import { OrderBook, canMove } from "../src/orders.ts";
import { expectedSignature, isSigned, isTimely } from "../src/webhooks/signature.ts";

const NOW = 1803902400;
const SECRET = "a-secret-for-tests";
const BODY = Buffer.from('{"id": "evt_r1"}');

test("a timestamp exactly 300 s away either way is timely", () => {
  assert.equal(isTimely(String(NOW - 300), NOW), true);
  assert.equal(isTimely(String(NOW + 300), NOW), true);
});

test("a timestamp 301 s away is not", () => {
  assert.equal(isTimely(String(NOW - 301), NOW), false);
});

test("a timestamp that is not whole seconds is not timely", () => {
  assert.equal(isTimely(`${NOW}abc`, NOW), false);
  assert.equal(isTimely("", NOW), false);
});

test("the provider's signature of these bytes is accepted", () => {
  const signature = expectedSignature(SECRET, String(NOW), BODY);

  assert.equal(isSigned(SECRET, { timestamp: String(NOW), signature, body: BODY }), true);
});

test("a short signature is refused without throwing", () => {
  assert.equal(isSigned(SECRET, { timestamp: String(NOW), signature: "3f9a", body: BODY }), false);
});

test("the same body with a moved timestamp is not signed", () => {
  const signature = expectedSignature(SECRET, String(NOW - 900), BODY);

  assert.equal(isSigned(SECRET, { timestamp: String(NOW), signature, body: BODY }), false);
});

test("a refunded payment cannot succeed again", () => {
  assert.equal(canMove("refunded", "succeeded"), false);
});

test("a failed payment can still succeed", () => {
  assert.equal(canMove("failed", "succeeded"), true);
});

test("an event of an unknown type keeps the state and takes its sequence number", () => {
  const book = new OrderBook();
  book.place({ id: "evt_a", type: "payment.succeeded", order: "ord_r", sequence: 1 });

  const placement = book.place({ id: "evt_b", type: "payment.note", order: "ord_r", sequence: 2 });

  assert.equal(placement, "ignored");
  assert.deepEqual(book.view("ord_r"), { order: "ord_r", state: "succeeded", sequence: 2 });
});
