import assert from "node:assert/strict";
import { test } from "node:test";

import {
  defaultLanguage,
  doneCommand,
  doneLines,
  hintText,
  startBody,
  startLine,
} from "../src/page/attempts.ts";
import type { DoneDocument } from "../src/page/types.ts";

const PASSED: DoneDocument = {
  slug: "two-sum",
  language: "kotlin",
  status: "passed",
  levels_finished: null,
  solve_s: 1120,
  rating: "ok",
  grade: "ok",
  caps: [],
  hints_used: 0,
  next_review: { due_on: "2026-10-27", in_days: 3, ease: 2.5 },
};

test("a problem with several languages starts in default_lang when it has it", () => {
  assert.equal(defaultLanguage({ kind: "function", languages: ["kotlin", "python"] }, "python"), "python");
});

test("a problem without default_lang starts in its first language", () => {
  assert.equal(defaultLanguage({ kind: "function", languages: ["go", "rust"] }, "python"), "go");
});

test("a project starts in its one language without --lang", () => {
  assert.equal(defaultLanguage({ kind: "project", languages: ["python"] }, "kotlin"), null);
});

test("an item starts without a language", () => {
  assert.equal(defaultLanguage({ kind: "item", languages: [] }, "python"), null);
});

test("default_lang is skipped for the first language the JDK can run", () => {
  const blocked = new Set(["java"]);
  assert.equal(defaultLanguage({ kind: "function", languages: ["java", "kotlin", "python"] }, "java", blocked), "kotlin");
});

test("a first language that is blocked gives way to the next one", () => {
  const blocked = new Set(["java", "kotlin"]);
  assert.equal(defaultLanguage({ kind: "function", languages: ["java", "kotlin", "go"] }, "python", blocked), "go");
});

test("a problem whose languages are all blocked keeps its usual default", () => {
  const blocked = new Set(["java", "kotlin"]);
  assert.equal(defaultLanguage({ kind: "function", languages: ["java", "kotlin"] }, "python", blocked), "java");
});

test("an empty time box starts without a timer", () => {
  assert.deepEqual(startBody({ slug: "two-sum", language: "python", fresh: false, minutes: " " }), {
    slug: "two-sum",
    language: "python",
    fresh: false,
    timer_minutes: null,
  });
});

test("a time box is sent in minutes", () => {
  assert.equal(startBody({ slug: "two-sum", language: null, fresh: true, minutes: "25" }).timer_minutes, 25);
});

test("the start line names every flag the dialog sets", () => {
  assert.equal(
    startLine({ slug: "two-sum", language: "python", fresh: true, minutes: "25" }),
    "cstudy start two-sum --lang python --fresh --timer 25m --no-open",
  );
});

test("the start line of a project has no --lang", () => {
  assert.equal(
    startLine({ slug: "bank-project-python", language: null, fresh: false, minutes: "" }),
    "cstudy start bank-project-python --no-open",
  );
});

test("a hint reads as cstudy hint heads it", () => {
  const hint = { hint: { number: 1, total: 2, markdown: "", html: "" } };
  assert.equal(hintText(hint), "hint 1 of 2");
});

test("a locked hint says the level it opens with", () => {
  assert.equal(hintText({ locked_until_level: 2 }), "no more hints until level 2 opens");
});

test("no hint left reads as cstudy hint prints it", () => {
  assert.equal(hintText({ exhausted: true }), "no more hints");
});

test("a rating finishes with --rating", () => {
  assert.equal(doneCommand("two-sum", { rating: "ok", gaveUp: false, notes: "" }), "cstudy done two-sum --rating ok");
});

test("giving up finishes with --gave-up and the notes quoted", () => {
  assert.equal(
    doneCommand("two-sum", { rating: null, gaveUp: true, notes: "ran out of time" }),
    "cstudy done two-sum --gave-up --notes 'ran out of time'",
  );
});

test("the outcome reads as the two lines cstudy done prints", () => {
  assert.deepEqual(doneLines(PASSED, null), [
    "two-sum · kotlin · passed · 18m 40s · rating ok · hints 0",
    "next review  2026-10-27 (in 3 days) · ease 2.50",
  ]);
});

test("a project's outcome names its levels and the levels cap", () => {
  const capped = { ...PASSED, slug: "bank-project-python", language: "python", status: "failed", levels_finished: 3, solve_s: 5040, grade: "hard", caps: ["levels"] };
  assert.equal(
    doneLines(capped, 4)[0],
    "bank-project-python · python · failed · levels 3 of 4 · 1h 24m · rating ok, capped at hard · hints 0",
  );
});

test("a hint cap leaves the rating as cstudy done words it", () => {
  assert.match(doneLines({ ...PASSED, grade: "ok", rating: "easy", caps: ["hint"] }, null)[0] ?? "", / · rating easy · /);
});

test("giving up reads as gave up", () => {
  assert.match(doneLines({ ...PASSED, status: "failed", rating: null, grade: "again" }, null)[0] ?? "", / · gave up · /);
});

test("an item's outcome has no language", () => {
  assert.equal(
    doneLines({ ...PASSED, slug: "url-shortener", language: null, solve_s: 42 }, null)[0],
    "url-shortener · passed · 42s · rating ok · hints 0",
  );
});

test("a review a day away reads in 1 day", () => {
  const tomorrow = { ...PASSED, next_review: { due_on: "2026-10-25", in_days: 1, ease: 2.36 } };
  assert.equal(doneLines(tomorrow, null)[1], "next review  2026-10-25 (in 1 day) · ease 2.36");
});
