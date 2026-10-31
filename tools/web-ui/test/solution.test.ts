import assert from "node:assert/strict";
import { test } from "node:test";

import { NO_SELECTION, solutionBody, solutionCommand } from "../src/page/solution.ts";

test("the default selection sends nothing but the confirmation", () => {
  assert.deepEqual(solutionBody(NO_SELECTION, false), { confirm: false });
});

test("a selection sends the fields cstudy solution takes", () => {
  const selection = { ...NO_SELECTION, language: "kotlin", approach: "hash-map", explanationOnly: true };
  assert.deepEqual(solutionBody(selection, true), {
    confirm: true,
    language: "kotlin",
    approach: "hash-map",
    explanation_only: true,
  });
});

test("all sends all instead of an approach", () => {
  assert.deepEqual(solutionBody({ ...NO_SELECTION, all: true }, false), { confirm: false, all: true });
});

test("the first broken reference is broken true", () => {
  assert.deepEqual(solutionBody({ ...NO_SELECTION, broken: true }, false), { confirm: false, broken: true });
});

test("the command names the selection as cstudy solution flags", () => {
  const selection = { ...NO_SELECTION, language: "python", approach: "brute-force", explanationOnly: true };
  assert.equal(
    solutionCommand("two-sum", selection),
    "cstudy solution two-sum --lang python --approach brute-force --explanation-only",
  );
});

test("a broken reference by id follows an equals sign", () => {
  assert.equal(
    solutionCommand("bounded-blocking-queue", { ...NO_SELECTION, broken: "if-not-while" }),
    "cstudy solution bounded-blocking-queue --broken=if-not-while",
  );
});

test("all and the first broken reference are bare flags", () => {
  assert.deepEqual(
    [solutionCommand("two-sum", { ...NO_SELECTION, all: true }), solutionCommand("queue", { ...NO_SELECTION, broken: true })],
    ["cstudy solution two-sum --all", "cstudy solution queue --broken"],
  );
});
