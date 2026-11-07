import assert from "node:assert/strict";
import { test } from "node:test";

import { listCommand, nextCommand, quoted, startCommand } from "../src/page/commands.ts";

test("the list command names each filter with its cstudy list flag", () => {
  assert.equal(
    listCommand({ status: "due", track: "dsa", lang: "kotlin" }),
    "cstudy list --track dsa --lang kotlin --status due",
  );
});

test("the list command names the label filters with their cstudy list flags", () => {
  assert.equal(
    listCommand({ scope: "function", role: "platform", domain: "backend" }),
    "cstudy list --domain backend --role platform --scope function",
  );
});

test("the list command without filters is bare", () => {
  assert.equal(listCommand({}), "cstudy list");
});

test("the next command takes only the filters cstudy next has", () => {
  assert.equal(
    nextCommand({ track: "dsa", status: "due", kind: "function", difficulty: "easy" }),
    "cstudy next --track dsa --difficulty easy",
  );
});

test("the next command takes the label filters", () => {
  assert.equal(
    nextCommand({ scope: "project", status: "due", domain: "fintech" }),
    "cstudy next --domain fintech --scope project",
  );
});

test("the list command names the set first", () => {
  assert.equal(listCommand({ track: "dsa", set: "backend-loop" }), "cstudy list --set backend-loop --track dsa");
});

test("the next command takes the set", () => {
  assert.equal(nextCommand({ set: "backend-loop", status: "due" }), "cstudy next --set backend-loop");
});

test("a start command names the language", () => {
  assert.equal(startCommand("two-sum", "kotlin"), "cstudy start two-sum --lang kotlin");
});

test("a start command without a language has no --lang", () => {
  assert.equal(startCommand("url-shortener", null), "cstudy start url-shortener");
});

test("a value a shell would split is quoted", () => {
  assert.equal(quoted("two pointers"), "'two pointers'");
});

test("a quote inside a quoted value is escaped", () => {
  assert.equal(quoted("it's"), "'it'\\''s'");
});

test("a plain value is not quoted", () => {
  assert.equal(quoted("arrays-hashing"), "arrays-hashing");
});

test("the list command names the search last, quoted when a shell needs it", () => {
  assert.equal(listCommand({ search: "two sum", track: "dsa" }), "cstudy list --track dsa --search 'two sum'");
});

test("the next command has no search", () => {
  assert.equal(nextCommand({ search: "two", track: "dsa" }), "cstudy next --track dsa");
});
