import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError, CSRF_HEADER, createApi, type Fetch } from "../src/page/api.ts";
import { AttemptFiles, conflictOf, fileUrl } from "../src/page/files.ts";

interface Sent {
  readonly path: string;
  readonly init: RequestInit;
}

function recording(status: number, body: string): { files: AttemptFiles; sent: Sent[] } {
  const sent: Sent[] = [];
  const fetcher: Fetch = async (path, init = {}) => {
    sent.push({ path, init });
    return new Response(status === 204 ? null : body, { status });
  };
  return { files: new AttemptFiles(createApi("the-token", fetcher), 7), sent };
}

const SAVED = '{"path": "bank/bank.py", "sha256": "new"}';

function header(sent: Sent[], name: string): string | null {
  return new Headers(sent[0]?.init.headers).get(name);
}

test("a file's URL keeps its slashes and escapes each segment", () => {
  assert.equal(fileUrl(7, "bank/my file#1.py"), "/api/v1/attempts/7/files/bank/my%20file%231.py");
});

test("a save puts the text", async () => {
  const { files, sent } = recording(200, SAVED);
  await files.save("bank/bank.py", "class Bank: ...\n", "old");
  assert.deepEqual([sent[0]?.init.method, sent[0]?.path, sent[0]?.init.body], [
    "PUT",
    "/api/v1/attempts/7/files/bank/bank.py",
    '{"text":"class Bank: ...\\n"}',
  ]);
});

test("a save names the ETag it read the file with", async () => {
  const { files, sent } = recording(200, SAVED);
  await files.save("bank/bank.py", "x", "old");
  assert.equal(header(sent, "If-Match"), '"old"');
});

test("a save sends the page's CSRF token", async () => {
  const { files, sent } = recording(200, SAVED);
  await files.save("bank/bank.py", "x", "old");
  assert.equal(header(sent, CSRF_HEADER), "the-token");
});

test("a save answers the new SHA-256", async () => {
  const { files } = recording(200, SAVED);
  assert.deepEqual(await files.save("bank/bank.py", "x", "old"), { path: "bank/bank.py", sha256: "new" });
});

test("a create asks for no file at the path", async () => {
  const { files, sent } = recording(201, SAVED);
  await files.create("bank/ledger.py", "LEDGER = []\n");
  assert.deepEqual([sent[0]?.init.method, header(sent, "If-None-Match"), header(sent, "If-Match")], ["PUT", "*", null]);
});

test("a move posts the new path with the file's ETag", async () => {
  const { files, sent } = recording(200, SAVED);
  await files.move("README.md", "docs/README.md", "abc");
  assert.deepEqual([sent[0]?.init.method, sent[0]?.path, sent[0]?.init.body, header(sent, "If-Match")], [
    "POST",
    "/api/v1/attempts/7/files/README.md/move",
    '{"to":"docs/README.md"}',
    '"abc"',
  ]);
});

test("a delete sends the file's ETag and takes an empty answer", async () => {
  const { files, sent } = recording(204, "");
  await files.remove("README.md", "abc");
  assert.deepEqual([sent[0]?.init.method, header(sent, "If-Match")], ["DELETE", '"abc"']);
});

test("a restore posts the path to the attempt", async () => {
  const { files, sent } = recording(200, '{"path": "README.md", "origin": "starter", "level": null}');
  const restored = await files.restore("README.md");
  assert.deepEqual([sent[0]?.path, sent[0]?.init.body, restored.origin], [
    "/api/v1/attempts/7/restore",
    '{"path":"README.md"}',
    "starter",
  ]);
});

test("a refusal keeps the error document's other fields", () => {
  const error = new ApiError(412, "precondition_failed", "changed", null, { sha256: "theirs" });
  assert.equal(error.details["sha256"], "theirs");
});

test("a stale save is a conflict naming the SHA-256 on disk now", async () => {
  const body = '{"error": {"code": "precondition_failed", "message": "README.md changed", "fix": null, "sha256": "theirs"}}';
  const { files } = recording(412, body);
  const refused = await files.save("README.md", "x", "old").catch((error: unknown) => error);
  assert.deepEqual(conflictOf(refused), { theirs: "theirs", message: "README.md changed" });
});

test("a save of a file deleted since is a conflict with nothing on disk", () => {
  const error = new ApiError(412, "precondition_failed", "gone", null, { sha256: null });
  assert.equal(conflictOf(error)?.theirs, null);
});

test("any other refusal is no conflict", () => {
  assert.equal(conflictOf(new ApiError(409, "locked", "busy")), null);
});
