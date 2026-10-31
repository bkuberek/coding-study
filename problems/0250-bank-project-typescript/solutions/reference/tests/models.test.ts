// Accounts and their balance history: the boundaries of moving money and of looking back.
import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { Account, BalanceHistory } from "../src/models.ts";

describe("BalanceHistory", () => {
  test("has no balance before its first change", () => {
    const history = new BalanceHistory();
    history.record(10, 0);
    assert.equal(history.balanceAt(9), undefined);
  });

  test("answers with the last of several changes at one moment", () => {
    const history = new BalanceHistory();
    history.record(10, 5);
    history.record(10, 8);
    assert.equal(history.balanceAt(10), 8);
  });

  test("holds a balance until the next change", () => {
    const history = new BalanceHistory();
    history.record(10, 5);
    history.record(20, 8);
    assert.equal(history.balanceAt(19), 5);
  });
});

describe("Account", () => {
  test("starts at zero when it is created", () => {
    assert.equal(new Account("ivy", 10).balanceAt(10), 0);
  });

  test("does not exist before it is created", () => {
    assert.equal(new Account("ivy", 10).balanceAt(9), undefined);
  });

  test("cannot send money to itself", () => {
    const account = new Account("ivy", 1);
    account.deposit(2, 50);
    assert.equal(account.canSend(account, 10), false);
  });

  test("counts the money it sends, never the money it receives", () => {
    const ivy = new Account("ivy", 1);
    const leo = new Account("leo", 1);
    ivy.deposit(2, 50);
    ivy.send(leo, 3, 20);
    leo.send(ivy, 4, 5);
    assert.equal(ivy.sent, 20);
  });

  test("absorbs the balance of a merged account", () => {
    const kept = new Account("kept", 1);
    const absorbed = new Account("gone", 2);
    kept.deposit(3, 10);
    absorbed.deposit(4, 40);
    kept.absorb(absorbed, 5);
    assert.equal(kept.balance, 50);
  });

  test("is its own holder while it is open", () => {
    const account = new Account("ivy", 1);
    assert.equal(account.holder, account);
  });

  test("is held through chained merges by the last account still open", () => {
    const [a, b, c] = ["a", "b", "c"].map((id) => new Account(id, 1));
    b.absorb(c, 2);
    a.absorb(b, 3);
    assert.equal(c.holder, a);
  });

  test("has no balance from the moment it is merged away", () => {
    const kept = new Account("kept", 1);
    const absorbed = new Account("gone", 2);
    kept.absorb(absorbed, 30);
    assert.equal(absorbed.balanceAt(30), undefined);
  });

  test("answers for times before it was merged away", () => {
    const kept = new Account("kept", 1);
    const absorbed = new Account("gone", 2);
    absorbed.deposit(5, 40);
    kept.absorb(absorbed, 30);
    assert.equal(absorbed.balanceAt(29), 40);
  });
});
