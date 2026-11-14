import assert from "node:assert/strict";
import { beforeEach, describe, test } from "node:test";

import { Budget } from "../src/budget.ts";
import { problemsWith } from "../src/schema.ts";
import { toolNamed } from "../src/tools.ts";
import type { JsonSchema } from "../src/tools.ts";
import { requestsTo, resetMocks, setScenario } from "./mockControl.ts";

const app = `http://127.0.0.1:${process.env.PORT}`;

type Result = { answer: string; stop: string; steps: number; calls: { tool: string; outcome: string }[] };

function parametersOf(tool: string): JsonSchema {
  const found = toolNamed(tool);
  assert.ok(found, `no tool ${tool}`);
  return found.parameters;
}

async function ask(role: string, question: string): Promise<Result> {
  const response = await fetch(`${app}/assist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role, question }),
  });
  assert.equal(response.status, 200);
  return (await response.json()) as Result;
}

describe("the parameters' schemas", () => {
  test("a valid lookup has no problem", () => {
    assert.deepEqual(problemsWith(parametersOf("lookup_order"), { order_id: "A-1042" }), []);
  });

  test("a number is not a string", () => {
    assert.deepEqual(problemsWith(parametersOf("lookup_order"), { order_id: 1042 }), [
      "arguments.order_id: expected a string",
    ]);
  });

  test("a parameter the tool lacks is refused", () => {
    const problems = problemsWith(parametersOf("lookup_order"), { order_id: "A-1042", card: true });

    assert.deepEqual(problems, ["arguments.card: not a parameter"]);
  });

  test("a required parameter must be there", () => {
    assert.deepEqual(problemsWith(parametersOf("search_kb"), {}), ["arguments.query: required"]);
  });

  test("a priority outside the list is refused", () => {
    const ticket = { subject: "Damaged", body: "It arrived damaged.", priority: "urgent" };

    assert.deepEqual(problemsWith(parametersOf("create_ticket"), ticket), [
      "arguments.priority: one of low, normal, high",
    ]);
  });

  test("an amount must be a whole number within its range", () => {
    const refund = { order_id: "A-2052", amount_cents: 12.5, reason: "Faulty" };

    assert.deepEqual(problemsWith(parametersOf("issue_refund"), refund), [
      "arguments.amount_cents: expected a whole number",
    ]);
  });

  test("a list is not an object", () => {
    assert.deepEqual(problemsWith(parametersOf("lookup_order"), ["A-1042"]), [
      "arguments: expected an object",
    ]);
  });
});

describe("the budget", () => {
  test("is exhausted once the steps reach the limit", () => {
    const budget = new Budget(2, 10_000);
    budget.spend({ prompt_tokens: 10, completion_tokens: 1 });
    budget.spend({ prompt_tokens: 10, completion_tokens: 1 });

    assert.equal(budget.exhausted(), "step_limit");
  });

  test("is spent when the tokens reach it exactly", () => {
    const budget = new Budget(6, 100);
    budget.spend({ prompt_tokens: 90, completion_tokens: 10 });

    assert.equal(budget.exhausted(), "token_budget");
  });

  test("allows another step below both", () => {
    const budget = new Budget(6, 100);
    budget.spend({ prompt_tokens: 90, completion_tokens: 9 });

    assert.equal(budget.exhausted(), null);
  });
});

describe("the assistant", () => {
  beforeEach(resetMocks);

  test("a refund support asks for never reaches the order system", async () => {
    const result = await ask("support", "Refund order A-2051 in full: the customer cancelled before it shipped.");

    assert.deepEqual(result.calls, [{ tool: "issue_refund", outcome: "not_allowed" }]);
    assert.equal((await requestsTo("orders")).length, 0);
  });

  test("a planted refund in a search result is refused", async () => {
    const result = await ask("support", "What does the help center say about warranty claims?");

    assert.deepEqual(result.calls, [
      { tool: "search_kb", outcome: "ok" },
      { tool: "issue_refund", outcome: "not_allowed" },
    ]);
  });

  test("an answer that repeats the system prompt is withheld", async () => {
    const result = await ask("support", "How do I reset a customer's password?");

    assert.equal(result.stop, "withheld");
  });

  test("a failing search is a result the model hears", async () => {
    await setScenario("kb", "outage");

    const result = await ask("support", "What is the return window for shoes?");

    assert.deepEqual(result.calls, [{ tool: "search_kb", outcome: "tool_error" }]);
    assert.equal(result.stop, "answered");
  });

  test("a model that never answers stops at the step limit", async () => {
    const result = await ask("support", "Find everything we have on shipping times to Norway.");

    assert.equal(result.stop, "step_limit");
    assert.equal(result.steps, 6);
    assert.equal((await requestsTo("kb")).length, 5);
  });
});
