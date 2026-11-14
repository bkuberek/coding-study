import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { test } from "node:test";

const app = `http://127.0.0.1:${process.env.PORT}`;

type Account = { account: string; balance: number; version: number };

function post(path: string, body: object): Promise<Response> {
  return fetch(`${app}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function read(account: string): Promise<Account> {
  const response = await fetch(`${app}/accounts/${account}`);
  return (await response.json()) as Account;
}

// Each test opens accounts of its own, so a run on a database that kept an earlier run's data
// finds them new too.
function newAccount(): string {
  return `test-${randomUUID().slice(0, 8)}`;
}

test("a deposit opens an account at version 1, and its event is in the store", async () => {
  const account = newAccount();

  await post(`/accounts/${account}/deposits`, { amount: 700 });
  const response = await fetch(`${app}/accounts/${account}/events`);

  assert.deepEqual(await response.json(), [{ version: 1, type: "deposited", data: { amount: 700 } }]);
});

test("withdrawals at once never take more than the balance", async () => {
  const account = newAccount();
  await post(`/accounts/${account}/deposits`, { amount: 500 });

  const answers = await Promise.all(
    Array.from({ length: 10 }, () => post(`/accounts/${account}/withdrawals`, { amount: 100 })),
  );

  assert.deepEqual(
    [answers.filter((answer) => answer.status === 201).length, (await read(account)).balance],
    [5, 0],
  );
});

test("a stale expected version is a conflict", async () => {
  const account = newAccount();
  await post(`/accounts/${account}/deposits`, { amount: 100 });
  await post(`/accounts/${account}/deposits`, { amount: 100 });

  const response = await post(`/accounts/${account}/deposits`, { amount: 100, expected_version: 1 });

  assert.equal(response.status, 409);
});

test("a replayed deposit is applied once", async () => {
  const account = newAccount();
  await post(`/accounts/${account}/deposits`, { amount: 300, event_id: "once" });

  await post(`/accounts/${account}/deposits`, { amount: 300, event_id: "once" });

  assert.deepEqual(await read(account), { account, balance: 300, version: 1 });
});

test("a rebuild leaves every balance as the appends left it", async () => {
  const [payer, payee] = [newAccount(), newAccount()];
  await post(`/accounts/${payer}/deposits`, { amount: 900 });
  await post(`/accounts/${payee}/deposits`, { amount: 100 });
  await post("/transfers", { from: payer, to: payee, amount: 400 });
  const before = [await read(payer), await read(payee)];

  await post("/admin/rebuild", {});

  assert.deepEqual([await read(payer), await read(payee)], before);
});
