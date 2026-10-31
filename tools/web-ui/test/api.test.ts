import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError, CSRF_HEADER, createApi, errorOf, type Fetch } from "../src/page/api.ts";

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
