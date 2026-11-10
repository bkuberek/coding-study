import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import { resetProviders } from "./providerScenario.ts";

const app = `http://127.0.0.1:${process.env.PORT}`;
const question = [{ role: "user", content: "When do badges renew?" }];

afterEach(resetProviders);

function ask(body: object): Promise<Response> {
  return fetch(`${app}/v1/chat`, {
    method: "POST",
    headers: { "X-Team": "tests", "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

test("the gateway answers its health path", async () => {
  const response = await fetch(`${app}/health`);

  assert.equal(response.status, 200);
});

test("a whole answer names its provider, its text and its usage", async () => {
  const response = await ask({ messages: question });

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    provider: "primary",
    content: "Badges renew every June.",
    usage: { prompt_tokens: 5, completion_tokens: 4 },
  });
});

test("a streamed answer ends with [DONE]", async () => {
  const response = await ask({ messages: question, stream: true });

  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/event-stream/);
  assert.ok((await response.text()).endsWith("data: [DONE]\n\n"));
});
