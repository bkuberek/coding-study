import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

import { call, signedUp, userName, written } from "./client.ts";

test("the service answers its health path", async () => {
  const response = await call("GET", "/health");

  assert.equal(response.status, 200);
});

test("a user reads back the note they wrote", async () => {
  const token = await signedUp("reader");
  const id = await written(token, "Groceries", "Milk, eggs, bread");

  const response = await call("GET", `/notes/${id}`, token);

  assert.deepEqual(await response.json(), { id, title: "Groceries", body: "Milk, eggs, bread" });
});

test("a deleted note is gone", async () => {
  const token = await signedUp("deleter");
  const id = await written(token, "Old idea");

  assert.equal((await call("DELETE", `/notes/${id}`, token)).status, 204);
  assert.equal((await call("GET", `/notes/${id}`, token)).status, 404);
});

test("a search finds the caller's notes by title, ignoring case", async () => {
  const token = await signedUp("searcher");
  const groceries = await written(token, "Groceries");
  await written(token, "Rent");

  const response = await call("GET", "/notes?q=GROCER", token);

  assert.deepEqual(await response.json(), [{ id: groceries, title: "Groceries" }]);
});

test("a user changes their display name", async () => {
  const token = await signedUp("renamer");

  const response = await call("PATCH", "/me", token, { display_name: "Ana Lima" });

  assert.equal(response.status, 200);
  const me = (await (await call("GET", "/me", token)).json()) as Record<string, string>;
  assert.equal(me.display_name, "Ana Lima");
  assert.equal(me.username, userName("renamer"));
});

test("a signed-in user downloads a shared file", async () => {
  const token = await signedUp("downloader");

  const response = await call("GET", "/attachments/handbook.txt", token);

  assert.equal(await response.text(), await readFile("attachments/handbook.txt", "utf8"));
});

test("a request without a session is refused", async () => {
  const response = await call("GET", "/me");

  assert.equal(response.status, 401);
});
