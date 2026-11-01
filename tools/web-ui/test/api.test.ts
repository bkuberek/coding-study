import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError, CSRF_HEADER, createApi, errorOf, FILE_SAVED_EVENT, type Fetch, type FileSaved } from "../src/page/api.ts";

function heard(events: EventTarget): FileSaved[] {
  const saved: FileSaved[] = [];
  events.addEventListener(FILE_SAVED_EVENT, (event) => saved.push((event as CustomEvent<FileSaved>).detail));
  return saved;
}

test("an error keeps the fields its document adds, such as the run holding a slot", () => {
  const error = errorOf(409, '{"error": {"code": "conflict", "message": "busy", "fix": null, "run": "c8a4"}}');
  assert.equal(error.details["run"], "c8a4");
});

test("saving a file of an attempt tells the page which one, and its SHA-256 now", async () => {
  const events = new EventTarget();
  const saved = heard(events);
  const { fetcher } = recording(200, '{"path": "bank/bank one.py", "sha256": "ab"}');
  await createApi("csrf", fetcher, events).put("/api/v1/attempts/7/files/bank/bank%20one.py", { text: "" });
  assert.deepEqual(saved, [{ attemptId: 7, path: "bank/bank one.py", sha256: "ab" }]);
});

test("saving a file through send tells the page which one", async () => {
  const events = new EventTarget();
  const saved = heard(events);
  const { fetcher } = recording(200, '{"path": "a.py", "sha256": "ab"}');
  await createApi("csrf", fetcher, events).send("PUT", "/api/v1/attempts/7/files/a.py", { body: { text: "" }, headers: { "If-Match": '"ab"' } });
  assert.deepEqual(saved, [{ attemptId: 7, path: "a.py", sha256: "ab" }]);
});

test("a save names the path the server cleaned, as a notification of it does", async () => {
  const events = new EventTarget();
  const saved = heard(events);
  const { fetcher } = recording(201, '{"path": "bank/a.py", "sha256": "ab"}');
  await createApi("csrf", fetcher, events).put("/api/v1/attempts/7/files/bank/./a.py", { text: "" });
  assert.equal(saved[0]?.path, "bank/a.py");
});

test("deleting or moving a file is no save", async () => {
  const events = new EventTarget();
  const saved = heard(events);
  const api = createApi("csrf", recording(200, "").fetcher, events);
  await api.send("DELETE", "/api/v1/attempts/7/files/a.py");
  await api.post("/api/v1/attempts/7/files/a.py/move", { to: "b.py" });
  assert.deepEqual(saved, []);
});

test("a save the server refused tells nothing", async () => {
  const events = new EventTarget();
  const saved = heard(events);
  const { fetcher } = recording(412, '{"error": {"code": "precondition_failed", "message": "stale", "fix": null}}');
  await assert.rejects(createApi("csrf", fetcher, events).put("/api/v1/attempts/7/files/a.py", { text: "" }));
  assert.deepEqual(saved, []);
});

test("storing the preferences saves no file", async () => {
  const events = new EventTarget();
  const saved = heard(events);
  const { fetcher } = recording(200, "{}");
  await createApi("csrf", fetcher, events).put("/api/v1/preferences", { vim: true });
  assert.deepEqual(saved, []);
});

interface Sent {
  readonly path: string;
  readonly init: RequestInit;
}

function recording(status: number, body: string): { fetcher: Fetch; sent: Sent[] } {
  const sent: Sent[] = [];
  const fetcher: Fetch = async (path, init = {}) => {
    sent.push({ path, init });
    return new Response(body, { status });
  };
  return { fetcher, sent };
}

test("a read answers the parsed document", async () => {
  const { fetcher } = recording(200, '{"api": 1}');
  assert.deepEqual(await createApi("csrf", fetcher).get("/api/v1/session"), { api: 1 });
});

test("a read sends no CSRF token", async () => {
  const { fetcher, sent } = recording(200, "{}");
  await createApi("csrf", fetcher).get("/api/v1/session");
  assert.equal(new Headers(sent[0]?.init.headers).has(CSRF_HEADER), false);
});

test("a write sends the page's CSRF token", async () => {
  const { fetcher, sent } = recording(200, "{}");
  await createApi("the-token", fetcher).put("/api/v1/preferences", { vim: true });
  assert.equal(new Headers(sent[0]?.init.headers).get(CSRF_HEADER), "the-token");
});

test("a write sends its body as JSON", async () => {
  const { fetcher, sent } = recording(200, "{}");
  await createApi("csrf", fetcher).put("/api/v1/preferences", { vim: true });
  assert.equal(sent[0]?.init.body, '{"vim":true}');
});

test("a post sends the page's CSRF token and its body as JSON", async () => {
  const { fetcher, sent } = recording(201, '{"attempt_id": 7}');
  await createApi("the-token", fetcher).post("/api/v1/attempts", { slug: "two-sum" });
  const init = sent[0]?.init;
  assert.deepEqual([init?.method, new Headers(init?.headers).get(CSRF_HEADER), init?.body], [
    "POST",
    "the-token",
    '{"slug":"two-sum"}',
  ]);
});

test("a post answers the parsed document", async () => {
  const { fetcher } = recording(201, '{"attempt_id": 7}');
  assert.deepEqual(await createApi("csrf", fetcher).post("/api/v1/attempts", {}), { attempt_id: 7 });
});

test("a refusal throws the error document's code and message", async () => {
  const body = '{"error": {"code": "usage", "message": "level 3 is locked", "fix": null}}';
  const { fetcher } = recording(422, body);
  await assert.rejects(createApi("csrf", fetcher).get("/api/v1/problems"), {
    name: "ApiError",
    code: "usage",
    message: "level 3 is locked",
    status: 422,
  });
});

test("an error keeps the CLI's fix hint", () => {
  const error = errorOf(503, '{"error": {"code": "environment", "message": "no pnpm", "fix": "brew install pnpm"}}');
  assert.equal(error.fix, "brew install pnpm");
});

test("a body that is not the error document becomes an internal error", () => {
  const error = errorOf(502, "<html>Bad gateway</html>");
  assert.deepEqual([error instanceof ApiError, error.code, error.message], [true, "internal", "the server answered 502"]);
});
