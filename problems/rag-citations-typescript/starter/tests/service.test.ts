import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";

import { requestEmbeddings } from "../src/providers.ts";
import { QUESTIONS } from "./corpus.ts";
import { resetProviders, sentBodies } from "./providerScenario.ts";

const app = `http://127.0.0.1:${process.env.PORT}`;

beforeEach(resetProviders);

test("the service answers its health path", async () => {
  const response = await fetch(`${app}/health`);

  assert.equal(response.status, 200);
});

test("the embeddings service gives a question it knows one vector of 9 numbers", async () => {
  const answer = await requestEmbeddings([QUESTIONS.refundWindow]);
  const body = answer.body as { data: { embedding: number[] }[] };

  assert.equal(answer.status, 200);
  assert.equal(body.data[0].embedding.length, 9);
});

test("the embeddings service refuses a text it does not know", async () => {
  const answer = await requestEmbeddings(["What is the meaning of life?"]);

  assert.equal(answer.status, 400);
});

test("the log shows what the embeddings service was sent", async () => {
  await requestEmbeddings([QUESTIONS.offsite]);

  assert.deepEqual(await sentBodies("embeddings"), [
    { model: "help-embed-1", input: [QUESTIONS.offsite] },
  ]);
});
