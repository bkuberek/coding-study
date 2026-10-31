import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError } from "../src/page/api.ts";
import { confirmed } from "../src/page/confirmation.ts";

const QUESTION = "Reveal the solution? The attempt will be graded as again.";

function guarded(): { sent: boolean[]; send: (confirm: boolean) => Promise<string> } {
  const sent: boolean[] = [];
  return {
    sent,
    send: async (confirm) => {
      sent.push(confirm);
      if (!confirm) throw new ApiError(409, "confirmation_required", QUESTION);
      return "revealed";
    },
  };
}

test("a request the server does not guard answers at once", async () => {
  assert.equal(await confirmed(async () => "shown", async () => false), "shown");
});

test("a guarded request asks the server's question", async () => {
  const asked: string[] = [];
  await confirmed(guarded().send, async (question) => {
    asked.push(question);
    return false;
  });
  assert.deepEqual(asked, [QUESTION]);
});

test("a yes sends the request again with confirm", async () => {
  const request = guarded();
  const answer = await confirmed(request.send, async () => true);
  assert.deepEqual([answer, request.sent], ["revealed", [false, true]]);
});

test("a no sends nothing more and answers null", async () => {
  const request = guarded();
  const answer = await confirmed(request.send, async () => false);
  assert.deepEqual([answer, request.sent], [null, [false]]);
});

test("any other refusal reaches the caller", async () => {
  const refused = async () => {
    throw new ApiError(422, "usage", "cstudy solution is locked during the mock interview");
  };
  await assert.rejects(confirmed(refused, async () => true), { code: "usage" });
});
