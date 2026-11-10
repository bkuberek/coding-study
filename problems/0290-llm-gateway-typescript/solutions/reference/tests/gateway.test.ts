import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import { resetProviders, setScenario } from "./providerScenario.ts";

const app = `http://127.0.0.1:${process.env.PORT}`;
const question = [{ role: "user", content: "When do badges renew?" }];

afterEach(resetProviders);

function ask(team: string, body: object): Promise<Response> {
  return fetch(`${app}/v1/chat`, {
    method: "POST",
    headers: { "X-Team": team, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function streamed(team: string): Promise<Response> {
  return ask(team, { messages: question, stream: true });
}

test("a dropped stream ends with an error event and no [DONE]", async () => {
  await setScenario("primary", "dropped_mid_stream");

  const text = await (await streamed("tests-drop")).text();

  assert.ok(text.endsWith('event: error\ndata: {"error":"the provider\'s stream ended early"}\n\n'));
  assert.ok(!text.includes("[DONE]"));
});

test("the secondary answers when the primary is down", async () => {
  await setScenario("primary", "outage");

  const text = await (await streamed("tests-fallback")).text();

  assert.match(text, /"provider":"secondary"/);
  assert.ok(text.endsWith("data: [DONE]\n\n"));
});

test("both providers down is a 502", async () => {
  await setScenario("primary", "outage");
  await setScenario("secondary", "overloaded");

  const response = await ask("tests-down", { messages: question });

  assert.equal(response.status, 502);
  assert.deepEqual(await response.json(), { error: "no provider answered" });
});

test("a team with nothing left is refused", async () => {
  await fetch(`${app}/v1/teams/tests-budget/budget`, {
    method: "PUT",
    body: JSON.stringify({ tokens: 9 }),
  });
  await (await streamed("tests-budget")).text();

  const response = await streamed("tests-budget");

  assert.equal(response.status, 429);
  assert.deepEqual(await response.json(), { error: "token budget exhausted" });
});

test("a team's usage counts its streamed answers", async () => {
  await (await streamed("tests-usage")).text();

  const response = await fetch(`${app}/v1/teams/tests-usage/usage`);

  assert.deepEqual(await response.json(), {
    team: "tests-usage",
    prompt_tokens: 5,
    completion_tokens: 4,
    cost_micros: 34,
    remaining_tokens: null,
  });
});
