// One test per finding of the review: the request it describes is refused or harmless now.

import assert from "node:assert/strict";
import { request } from "node:http";
import { test } from "node:test";

import { call, signedUp, userName, written } from "./client.ts";

test("another user's note answers 404 to a read and to a delete, and stays", async () => {
  const owner = await signedUp("owner");
  const other = await signedUp("other");
  const id = await written(owner, "Salary review", "Private");

  assert.equal((await call("GET", `/notes/${id}`, other)).status, 404);
  assert.equal((await call("DELETE", `/notes/${id}`, other)).status, 404);
  assert.equal((await call("GET", `/notes/${id}`, owner)).status, 200);
});

/** The status of a GET sent with its path as written: `fetch` would resolve a literal `..`. */
function rawStatus(path: string, token: string): Promise<number> {
  return new Promise((resolve, reject) => {
    const headers = { Authorization: `Bearer ${token}` };
    request({ host: "127.0.0.1", port: process.env.PORT, path, headers }, (response) => {
      response.resume();
      resolve(response.statusCode ?? 0);
    })
      .on("error", reject)
      .end();
  });
}

const climbs = ["../package.json", "..%2Fpackage.json", "%2e%2e%2fpackage.json"];
for (const [index, name] of climbs.entries()) {
  test(`a name that leaves the attachments folder answers 404: ${name}`, async () => {
    const token = await signedUp(`climber${index}`);

    assert.equal(await rawStatus(`/attachments/${name}`, token), 404);
  });
}

test("a role in a body changes nothing, on a profile or a new account", async () => {
  const token = await signedUp("promoter");

  await call("PATCH", "/me", token, { display_name: "Eve", role: "admin" });
  const created = await call("POST", "/users", undefined, {
    username: userName("eve"),
    password: "notes-pass-1234",
    role: "admin",
  });

  assert.equal(((await created.json()) as { role: string }).role, "member");
  assert.equal((await call("GET", "/admin/users", token)).status, 403);
});

test("a quote in a search finds the caller's own notes, and only those", async () => {
  const token = await signedUp("quoter");
  const other = await signedUp("bystander");
  const id = await written(token, "O'Brien contract");
  await written(other, "Payroll");

  const injected = await call("GET", `/notes?q=${encodeURIComponent("' OR '1'='1")}`, token);
  const quoted = await call("GET", `/notes?q=${encodeURIComponent("O'Brien")}`, token);

  assert.deepEqual(await injected.json(), []);
  assert.deepEqual(await quoted.json(), [{ id, title: "O'Brien contract" }]);
});

test("an error answers its code and nothing else", async () => {
  const token = await signedUp("breaker");

  const response = await call("POST", "/notes", token, '{"title": ');

  assert.equal(response.status, 400);
  assert.deepEqual(await response.json(), { error: "invalid_request" });
});
