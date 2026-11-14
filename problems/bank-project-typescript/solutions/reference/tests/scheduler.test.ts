// The run order of booked transfers, without a bank around them.
import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { type ScheduledTransfer, TransferScheduler } from "../src/scheduler.ts";

function dueAt(due: number, amount = 10): ScheduledTransfer {
  return { sourceId: "payer", targetId: "payee", amount, due };
}

describe("TransferScheduler", () => {
  test("numbers bookings from one", () => {
    const scheduler = new TransferScheduler();
    const ids = [scheduler.book(dueAt(5)), scheduler.book(dueAt(5))];
    assert.deepEqual(ids, ["transfer1", "transfer2"]);
  });

  test("hands out the earliest due transfer first", () => {
    const scheduler = new TransferScheduler();
    const late = dueAt(20);
    const early = dueAt(10);
    scheduler.book(late);
    scheduler.book(early);
    assert.deepEqual(scheduler.takeDue(20), [early, late]);
  });

  test("hands out transfers due at the same time in booking order", () => {
    const scheduler = new TransferScheduler();
    for (const amount of [1, 2, 3]) scheduler.book(dueAt(10, amount));
    const amounts = scheduler.takeDue(10).map((transfer) => transfer.amount);
    assert.deepEqual(amounts, [1, 2, 3]);
  });

  test("keeps transfers that are due later", () => {
    const scheduler = new TransferScheduler();
    scheduler.book(dueAt(11));
    assert.deepEqual(scheduler.takeDue(10), []);
  });

  test("drops a cancelled transfer", () => {
    const scheduler = new TransferScheduler();
    scheduler.cancel(scheduler.book(dueAt(10)));
    assert.deepEqual(scheduler.takeDue(10), []);
  });

  test("a transfer handed out is no longer pending", () => {
    const scheduler = new TransferScheduler();
    const transferId = scheduler.book(dueAt(10));
    scheduler.takeDue(10);
    assert.equal(scheduler.findPending(transferId), undefined);
  });

  test("cancels a transfer once", () => {
    const scheduler = new TransferScheduler();
    const transferId = scheduler.book(dueAt(10));
    scheduler.cancel(transferId);
    assert.equal(scheduler.cancel(transferId), false);
  });

  test("cannot cancel an id it never booked", () => {
    assert.equal(new TransferScheduler().cancel("transfer1"), false);
  });
});
