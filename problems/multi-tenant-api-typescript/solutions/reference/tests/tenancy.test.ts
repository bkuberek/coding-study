import assert from "node:assert/strict";
import { test } from "node:test";

const app = `http://127.0.0.1:${process.env.PORT}`;

function as(key: string, init: RequestInit = {}): RequestInit {
  return { ...init, headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" } };
}

async function idsOf(response: Response): Promise<string[]> {
  const rows = (await response.json()) as { id: string }[];
  return rows.map((row) => row.id).sort();
}

test("an organization lists only its own projects", async () => {
  const response = await fetch(`${app}/projects`, as("key-bea"));

  assert.deepEqual(await idsOf(response), ["p-3"]);
});

test("another organization's project is not found rather than forbidden", async () => {
  const response = await fetch(`${app}/projects/p-3`, as("key-ada"));

  assert.equal(response.status, 404);
});

test("a search finds only the caller's tasks though its query names no organization", async () => {
  const response = await fetch(`${app}/search/tasks?q=launch`, as("key-bea"));

  assert.deepEqual(await idsOf(response), ["t-4"]);
});

test("a member may not delete a project of their own organization", async () => {
  const response = await fetch(`${app}/projects/p-1`, as("key-ari", { method: "DELETE" }));

  assert.equal(response.status, 403);
});

test("a project created with another organization's id in its body stays the caller's", async () => {
  const body = JSON.stringify({ name: "Taxes", tenant_id: "birch" });
  const created = await fetch(`${app}/projects`, as("key-ada", { method: "POST", body }));
  const { id } = (await created.json()) as { id: string };

  const seen = await fetch(`${app}/projects/${id}`, as("key-bea"));

  assert.equal(seen.status, 404);
});

test("reads from two organizations at once each see their own rows", async () => {
  const reads = Array.from({ length: 20 }, (_, index) =>
    index % 2 === 0
      ? fetch(`${app}/tasks/t-1`, as("key-ada"))
      : fetch(`${app}/tasks/t-4`, as("key-bea")),
  );

  const statuses = (await Promise.all(reads)).map((response) => response.status);

  assert.deepEqual(new Set(statuses), new Set([200]));
});
